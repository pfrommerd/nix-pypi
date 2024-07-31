from dataclasses import dataclass
from pathlib import Path

from .core import Recipe, URLDistribution

import base64
import re
import os
import hashlib

@dataclass
class NixExporter:
    nixpkgs_overrides : set[str]
    def recipe_ident(self, target_id, env_recipes, build_recipes) -> str:
        # if the target is in the environment, we use the name
        # otherwise we use the full id (with the version + extras hash)
        if target_id in env_recipes:
            name = env_recipes[target_id].name
            return name
        elif target_id in build_recipes:
            r = build_recipes[target_id]
            return r.id.replace(".", "_")
        else:
            env_recipes = ", ".join(env_recipes.keys())
            build_recipes = ", ".join(build_recipes.keys())
            raise ValueError(f"Target ID not found: {target_id} in {env_recipes}; build: {build_recipes}")

    def source_expr(self, dist, root_path):
        if isinstance(dist, URLDistribution):
            url = dist.url
            url_parsed = dist.parsed_url
            if url_parsed.scheme != "file":
                hash = bytes.fromhex(dist.content_hash)
                hash = base64.b64encode(hash).decode("utf-8")
                hash = f"sha256-{hash}"
                return f"""fetchurl {{
                    url="{url}";
                    hash="{hash}";
                }}"""
            else:
                file_path = Path(url_parsed.path).resolve()
                relative_path = os.path.relpath(str(file_path), str(root_path))
                try:
                    relative_path = file_path.relative_to(root_path)
                    return f"./{relative_path}"
                except ValueError:
                    return f"{file_path}"
        else:
            raise ValueError(f"Unsupported distribution type: {dist}")

    def build_expression(self, recipe, env, env_recipes, build_recipes, recipes, root_path):
        if recipe.name in self.nixpkgs_overrides:
            return f"python.pkgs.{recipe.name}"
        dist = recipe.project.distribution
        src = self.source_expr(dist, root_path)
        format = recipe.project.format
        recipe_ident = lambda target_id: self.recipe_ident(target_id, env_recipes, build_recipes)

        if format == "nix":
            # find all of the packages in the build environment
            nix_env = {recipes[r].name : recipe_ident(r) for r in recipe.env}
            nix_env = " ".join(f"{k} = {v};" for k, v in nix_env.items())
            return f"""
            let env = with packages; with buildPackages; {{{nix_env}}}; in 
            (import {src}) {{
                buildPythonPackage=buildPythonPackage;
                env=env;
                fetchurl=fetchurl;
                nixpkgs=nixpkgs;
                python=python;
            }}"""

        # construct the dependencies
        deps = {r.name for r in recipe.target.dependencies}

        # if the recipe is in the environment, the dependencies should be the environment dependencies.
        # Otherwise, the dependencies are the build dependencies.
        if recipe.id in env_recipes:
            dependencies = " ".join(recipe_ident(env[r.name].id) for r in recipe.target.dependencies)
        else: # otherwise the dependencies are whatever the build environment has resolved to
            dependencies = " ".join(recipe_ident(r) for r in recipe.env if recipes[r].name in deps)

        if dependencies:
            dependencies = f"dependencies = with packages; with buildPackages; [{dependencies}];"
        if dist.is_wheel:
            build_system = "" 
        else:
            build_deps = {r.name for r in recipe.target.build_dependencies}
            build_system = " ".join(recipe_ident(r) for r in recipe.env if recipes[r].name in build_deps)
            build_system = f"build-system = with packages; with buildPackages; [{build_system}];"
        if format == "pyproject" or format == "pyproject/poetry":
            format = f'format="pyproject";'
        elif format == "wheel":
            format = 'format="wheel";'
        else:
            format = ""
        return f"""buildPythonPackage {{
            pname = "{recipe.name}";
            version = "{recipe.version}";
            {format}
            src = {src};
            {build_system}
            {dependencies}
            doCheck = false;
        }}"""

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
                expr_path: Path,
                env_recipes : dict[str, Recipe], 
                build_recipes : dict[str, Recipe],
            ) -> str:
        root_path = expr_path.parent
        recipes = {}
        recipes.update(build_recipes)
        recipes.update(env_recipes)

        env = {r.name : r for r in env_recipes.values()}
        recipe_ident = lambda target_id: self.recipe_ident(target_id, env_recipes, build_recipes)
        build_exp = lambda recipe: self.build_expression(recipe, env, env_recipes, build_recipes, recipes, root_path)

        pkgsExpr = "\n".join([f"{recipe_ident(r.id)} = {build_exp(r)};" for r in env_recipes.values()])
        pkgsExpr = f"{{{pkgsExpr}}}"
        buildPkgsExpr = "\n".join([f"{recipe_ident(r.id)} = {build_exp(r)};" for r in build_recipes.values()])
        buildPkgsExpr = f"{{{buildPkgsExpr}}}"
        inputs = "{buildPythonPackage, fetchurl, nixpkgs, python}"
        expr = f"""rec {{
            packages = rec {pkgsExpr};
            buildPackages = rec {buildPkgsExpr};
        }}"""
        expr = self.format_expr(expr)
        return f"{inputs}: {expr}"