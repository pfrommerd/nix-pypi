from dataclasses import dataclass, field
from pathlib import Path

from typing import Callable, Any

from .core import URLDistribution, Version, Target, SystemInfo
from .resolver import Environment

import logging
import importlib
import base64
import re
import pathlib
import shutil
import os

logger = logging.getLogger(__name__)

NixExporter = Any


@dataclass
class NixPyPackage:
    name: str
    variants: dict[Version, dict[frozenset[str], set[Target]]] = field(default_factory=dict)

    def add_target(self, t : Target):
        extra_variants = self.variants.setdefault(t.version, {})
        with_extras = frozenset(t.candidate.with_extras)
        extra_variants.setdefault(with_extras, set()).add(t)

    def format_target_lookup(self, target: Target):
        base = target.candidate.name
        if len(self.variants) > 1:
            base = f"{base}.v{str(target.candidate.version).replace('.','_')}"
        extras_variants = self.variants[target.candidate.version]
        if len(extras_variants) > 1:
            base = f"{base}.{NixPyPackage.format_variant_set(target.candidate.with_extras)}"
        target_variants = extras_variants[frozenset(target.candidate.with_extras)]
        system_variants = {}
        for t in target_variants:
            system_variants.setdefault(t.candidate.system, set()).add(t)
        include_target_id = any(len(v) > 1 for v in system_variants.values())
        if include_target_id:
            # use the first 8 characters of the target id to disambiguate 
            # the target if there are multiple variants for any of the target systems
            # (potentially due to different environment dependencies between different targets)
            base = f"{base}.d{target.hash[:8]}"
        return base

    @staticmethod
    def format_variant_set(k):
        if not k:
            return "default"
        return "with_" + "_".join(sorted(k))
    
    @staticmethod
    def target_expr(target: Target, exporter: NixExporter, 
                    resolve_target: Callable[[str], Target], resolve_target_id: Callable[[str], str]):
        dist = target.project.distribution

        if target.project.format == "nix":
            build_system, dependencies = "{}", "{}"
            if target.build_dependencies:
                build_system = f"""with packages; {{
                        {' '.join(f"{resolve_target(t).name} = {resolve_target_id(t)};" for t in target.build_dependencies)}
                    }}"""
            if target.dependencies:
                dependencies = f"""with packages; {{
                        {' '.join(f"{resolve_target(t).name} = {resolve_target_id(t)};" for t in target.dependencies)}
                    }}"""
            # import the target directly
            if dist.local:
                path = Path("/" + dist.parsed_url.path).resolve()
                local = False
                for p in exporter.custom_paths:
                    try:
                        custom_name = path.relative_to(p.resolve()).name.replace(".", "_").replace("-", "_")
                        import_expr = f"nixpy-custom.{custom_name}"
                        local = True
                        break
                    except ValueError:
                        pass
                if not local:
                    logger.error(f"Could not find custom path for {path}")
                    raise ValueError(f"Could not find custom path for {path}")
            else:
                hash = bytes.fromhex(dist.content_hash)
                hash = base64.b64encode(hash).decode("utf-8")
                hash = f"sha256-{hash}"
                import_expr = f"(import (fetchurl {{ url=\"{dist.url}\"; hash=\"{hash}\"; }}))"
            return f"""{import_expr} {{
                buildPythonPackage=buildPythonPackage;
                build_system={build_system};
                dependencies={dependencies};
                fetchurl=fetchurl;
                nixpkgs=nixpkgs;
                python=python;
            }}"""

        formatLine = "format=\"wheel\";" if target.project.format == "wheel" else \
                "format=\"pyproject\";" if target.project.format == "pyproject" else ""
        if dist.local:
            try:
                path = Path("/" + dist.parsed_url.path).resolve()
                relative = path.relative_to(exporter.root_path)
                src = f"./{relative}"
            except ValueError:
                logger.error(f"Could not resolve path {dist.parsed_url.path}")
                raise ValueError(f"Could not resolve path {dist.parsed_url.path}")
        else:
            hash = bytes.fromhex(dist.content_hash)
            hash = base64.b64encode(hash).decode("utf-8")
            hash = f"sha256-{hash}"
            src = f"fetchurl {{ url=\"{dist.url}\"; hash=\"{hash}\"; }}"
        
        build_system, dependencies = "", ""
        if target.build_dependencies:
            build_system = f"build_system = with packages; [{' '.join(resolve_target_id(t) for t in target.build_dependencies)}];"
        if target.dependencies:
            dependencies = f"dependencies = with packages; [{' '.join(resolve_target_id(t) for t in target.dependencies)}];"
        return f"""buildPythonPackage {{
            pname = "{target.name}";
            version = "{target.version}";
            {formatLine}
            src = {src};
            {build_system}
            {dependencies}
        }}
        """

    @staticmethod
    def targets_expr(target_variants: set[Target], exporter: NixExporter,
                     resolve_target: Callable[[str], Target], resolve_target_id: Callable[[str], str]):
        # organize the targets by system
        system_variants : dict[SystemInfo, set[Target]] = {}
        for t in target_variants:
            system_variants.setdefault(t.candidate.system, set()).add(t)
        include_target_id = any(len(v) > 1 for v in system_variants.values())
        if not include_target_id:
            system_variants = {k: next(iter(v)) for k, v in system_variants.items()}
            expressions : dict[str, str] = {k.nix_platform: NixPyPackage.target_expr(v, exporter, resolve_target, resolve_target_id) for k, v in system_variants.items()}
            if len(set(expressions.values())) == 1:
                return next(iter(expressions.values()))
            else:
                variants = f"{{{" ".join(f"{k} = {v};" for k, v in expressions.items())}}}"
                return f"{variants}.${{nixpkgs.system}}"
        else:
            expressions : dict[str, str] = {}
            for k, v in system_variants.items():
                target_variants = {t.hash[:8] : NixPyPackage.target_expr(t, exporter, resolve_target, resolve_target_id) for t in v}
                expressions[k.nix_platform] = f"{{{" ".join(f"d{k} = {v};" for k, v in target_variants.items())}}}"
            system_variants = f"{{{" ".join(f"{k} = {v};" for k, v in expressions.items())}}}"
            return f"{system_variants}.${{nixpkgs.system}}"

    @staticmethod
    def version_expr(extra_variants: dict[frozenset[str], set[Target]], exporter: NixExporter, 
                     resolve_target: Callable[[str], Target], resolve_target_id: Callable[[str], str]):
        if len(extra_variants) == 1:
            target = next(iter(extra_variants.values()))
            return NixPyPackage.targets_expr(target, exporter, resolve_target, resolve_target_id)
        else:
            return f"""{{
                {" ".join(f"{NixPyPackage.format_variant_set(k)} = {NixPyPackage.targets_expr(v, exporter, resolve_target, resolve_target_id)};" for k, v in extra_variants.items())}
            }}"""

    # returns the expression, taking in
    # a function that maps target ids to the nix expression
    # for that target
    def expression(self, exporter: NixExporter, resolve_target: Callable[[str], Target], resolve_target_id: Callable[[str], str]):
        if len(self.variants) == 1:
            version = next(iter(self.variants.values()))
            return NixPyPackage.version_expr(version, exporter, resolve_target, resolve_target_id)
        else:
            return f"""{{
                {" ".join(f"v{str(k).replace(".","_")} = {self.version_expr(v, exporter, resolve_target, resolve_target_id)};" for k, v in self.variants.items())}
            }}"""

@dataclass
class NixExporter:
    custom_paths: list[Path]
    root_path: Path

    def format_expr(self, expr):
        # replace all multiple spaces
        # outside of strings by a single space
        # expr = re.sub(r"[\s]+", " ", expr)
        expr = re.sub(r'[\s]+(?=(?:[^"]*"[^"]*")*[^"]*$)', " ", expr)
        expr = expr.replace("{", "{\n").replace("}", "\n}").replace(";", ";\n")
        lines = []
        ident = 0
        pat = re.compile(r"[\s]+")
        for l in expr.split("\n"):
            l = l.strip()
            if not l: continue
            if l.startswith("}"):
                ident = ident - 1
            lines.append("  "*ident + l)
            if l.endswith("{"):
                ident = ident + 1
        expr = "\n".join(lines)
        return expr

    def expression(self, 
                environments : list[Environment]
            ) -> str:
        packages = {}
        # populate the main environment packages
        for e in environments:
            for t in e.targets.values():
                if t.name not in packages:
                    packages.setdefault(t.name, NixPyPackage(t.name))

        # populate the targets

        packages : dict[str, NixPyPackage] = {}
        platformEnvs : dict[SystemInfo, set[str]] = {}
        targets = {}
        for e in environments:
            targets.update(e.targets)
            for t in e.targets.values():
                packages.setdefault(t.name,  NixPyPackage(t.name))
                packages[t.name].add_target(t)
                if t.id in e.env:
                    platformEnvs.setdefault(e.system_info, set()).add(t.id)
        def resolve_target(t_id):
            return targets[t_id]
        def resolve_target_id(t_id):
            target = targets[t_id]
            return packages[target.name].format_target_lookup(target)
        envsExpr = {s.nix_platform: " ".join(f"{targets[t].name} = {resolve_target_id(t)};" for t in v) for s, v in platformEnvs.items()}
        envsExpr = f"""{{
            {" ".join(f"{k} = with packages; {{ {v} }};" for k, v in envsExpr.items())}
        }}"""
        expr = f"""rec {{
            packages = rec {{
                {"".join(f"{p.name} = {p.expression(self, resolve_target, resolve_target_id)};" for p in packages.values())}
            }};
            envs = {envsExpr};
            env = envs.${{nixpkgs.system}};
        }}
        """
        inputs = "{buildPythonPackage, fetchurl, nixpkgs, python, nixpy-custom ? {}}"
        expr = self.format_expr(expr)
        return f"{inputs}: {expr}"