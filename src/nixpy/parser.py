# Contains tools for parsing the project
# information from either binary or distribution distributions

from email.message import EmailMessage
from email.parser import BytesParser

from dataclasses import dataclass, field, replace

from .core import Project, Version, Distribution, Requirement
from .resources import Resources
from packaging.version import InvalidVersion
from packaging.requirements import InvalidRequirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from pathlib import Path
from typing import IO, Any
from string import Template

import glob
import re
import asyncio
import subprocess
import tempfile
import zipfile
import tomllib
import tarfile
import urllib.parse

import logging
logger = logging.getLogger(__name__)

class ParseError(RuntimeError): ...

class Parser:
    def ensure_default_build_deps(project):
        return project
        # don't include any defaults
        # for the build backends themselves (or their dependencies)
        if project.name in {"setuptools", "pip", 
                    "wheel", "flit-core", "hatchling", 
                    "poetry-core", "pdm-core", "pyproject-hooks",
                    "build", "packaging"}:
            return project
        build_dependencies = list(project.build_dependencies)
        deps = {d.name : d for d in build_dependencies}
        if not "setuptools" in deps:
            build_dependencies.append(Requirement("setuptools>=70"))
        if not "pip" in deps:
            build_dependencies.append(Requirement("pip>=24"))
        if not "wheel" in deps:
            build_dependencies.append(Requirement("wheel>=0.43"))
        if not "build" in deps:
            build_dependencies.append(Requirement("build>=1.2.1"))
        if not "packaging" in deps:
            build_dependencies.append(Requirement("packaging>=19.1"))
        return replace(project, build_dependencies=build_dependencies)

@dataclass
class PyProjectParser:
    @staticmethod
    def parse_toml(toml_str, project_root):
        env = {
            "PROJECT_ROOT": str(project_root),
            "PWD": str(project_root)
        }
        for k,v in env.items():
            toml_str = toml_str.replace(f"${k}",v)
            toml_str = toml_str.replace(f"${{{k}}}",v)
        return tomllib.loads(toml_str)

    async def parse_poetry(self, distribution: Distribution, poetry_data : dict[str, Any], version_hint: str | None = None) -> Project:
        name = poetry_data.get("name", None)
        version = poetry_data.get("version", None)
        version = Version(version) if version is not None else version_hint
        if name is None: raise ParseError("No name entry in poetry data")
        if version is None: raise ParseError("Unable to determine poetry version")
        req_python = None
        dependencies = []
        build_dependencies = []

        def parse_poetry_version_spec(version):
            if not version: return ""
            version = version.strip()
            if version.startswith("^"):
                version = version.lstrip("^")
                return f"~={version}"
            if not version.startswith(">") or version.startswith("<"):
                return f"=={version}"
            return version
        def parse_poetry_req(n, d):
            n = canonicalize_name(n)
            if isinstance(d, str):
                v = parse_poetry_version_spec(d)
                r = Requirement(f"{n}{v}")
            elif isinstance(d, dict):
                v = parse_poetry_version_spec(d.get("version", None))
                r = Requirement(f"{n}{v}")
            return r

        for n, d in poetry_data.get("dependencies").items():
            r = parse_poetry_req(n, d)
            if r.name == "python":
                req_python = r.specifier
            else:
                dependencies.append(r)
        project = Project(
            canonicalize_name(name), version, "pyproject/poetry",
            req_python, distribution, dependencies,
            build_dependencies
        )
        project = Parser.ensure_default_build_deps(project)
        return project

    async def parse(self, distribution: Distribution, toml_path : Path, version_hint : str | None = None) -> Project:
        with open(toml_path, "r") as f:
            data = PyProjectParser.parse_toml(f.read(), toml_path.parent.resolve())
        project = data.get("project", None)
        if project is None:
            poetry_data = data.get("tool", {}).get("poetry", {})
            if poetry_data:
                return await self.parse_poetry(distribution, poetry_data, version_hint)
            raise ParseError(f"No project entry in pyproject.toml: {toml_path}")
        name = project.get("name", None)
        if name is None: raise ParseError("No name entry in pyproject.toml")
        version = project.get("version", None)
        version = Version(version) if version is not None else version_hint
        if version is None: raise ParseError("Unable to determine pyproject version")
        req_python = None
        deps = [Requirement(r) for r in project.get("dependencies", [])]

        # parse the build requirements
        build_deps = [Requirement(r) for r in data.get("build-system", {}).get("requires", [])]
        for r in deps: r.name = canonicalize_name(r.name)
        for r in build_deps: r.name = canonicalize_name(r.name)
        feature_deps = {
            k: [Requirement(r) for r in v] for (k,v) in project.get("optional-dependencies", {}).items()
        }
        project = Project(
            canonicalize_name(name), version,
            "pyproject",
            req_python, distribution,
            deps,  build_deps
        )
        project = Parser.ensure_default_build_deps(project)
        return project
    
    async def parse_tool_info(self, toml_path: Path, tool_name : str) -> dict[str, str]:
        with open(toml_path, "r") as f:
            data = PyProjectParser.parse_toml(f.read(), toml_path.parent.resolve())
        tools = data.get("tool", {})
        return tools.get(tool_name, {})

    @staticmethod
    async def parse_pyproject_build_deps(toml: Path | dict) -> list[Requirement]:
        if isinstance(toml, dict):
            data = toml
        else:
            with open(toml, "r") as f:
                data = PyProjectParser.parse_toml(f.read(), toml.parent.resolve())
        build_deps = [Requirement(r) for r in data.get("build-system", {}).get("requires", [])]
        for r in build_deps: r.name = canonicalize_name(r.name)
        return build_deps

@dataclass
class SetuptoolsParser:
    async def parse(self, distribution: Distribution, setup_py_path : Path) -> Project:
        cwd = setup_py_path.parent.resolve()
        proc = await asyncio.create_subprocess_exec(
            "python3", "setup.py", "egg_info",
            cwd=cwd, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        msg, _ = await proc.communicate()
        msg = msg.decode("utf-8")
        match = re.search(r"writing ([\.\-\/\w]*\/PKG-INFO)", msg)
        if match is None:
            paths = glob.iglob("**/PKG-INFO", root_dir=cwd, recursive=True)
            try:
                info = next(paths)
            except StopIteration as e:
                raise ValueError(f"Can't parse setup.py: {setup_py_path}\n{msg}")
        else:
            info = match.group(1)
        info = cwd / info
        with open(info, "rb") as f:
            project = await MetadataParser().parse(distribution, f)
        
        # parse the build dependencies specially
        build_dependencies = list(project.build_dependencies)
        deps = {d.name : d for d in build_dependencies}
        if not "setuptools" in deps:
            build_dependencies.append(Requirement("setuptools>=70"))

        pyproject_path = cwd / "pyproject.toml"
        if pyproject_path.exists():
            build_dependencies.extend(await PyProjectParser.parse_pyproject_build_deps(pyproject_path))
        # add a recent setuptools version to the build dependencies if necessary
        project = replace(project,
            format="setuptools", build_dependencies=build_dependencies
        )
        project = Parser.ensure_default_build_deps(project)
        return project


@dataclass
class MetadataParser:
    async def parse(self, distribution: Distribution, file: IO | EmailMessage) -> Project:
        if hasattr(file, "get") and hasattr(file, "get_all"):
            msg = file
        else:
            p = BytesParser()
            msg = p.parse(file, headersonly=True)
        name = msg.get("Name", None)
        if name is None:
            raise ParseError(f"No name in: {msg}")
        version = msg.get("Version", None)
        if version is None:
            raise ParseError(f"No version in: {msg}")
        deps = msg.get_all("Requires-Dist", [])
        try:
            deps = list([Requirement(r) for r in deps])
        except InvalidRequirement as e:
            raise ParseError(e)
        req_python = msg.get("Requires-Python")
        req_python = SpecifierSet(req_python) if req_python else None
        # canonicalize dependency names
        for r in deps: r.name = canonicalize_name(r.name)
        return Project(
            canonicalize_name(name), Version(version), "metadata",
            req_python, distribution,
            deps, []
        )

# Will parse a distribution distribution
@dataclass
class SrcDistParser:
    pyproject_parser : PyProjectParser = field(default_factory=lambda: PyProjectParser())
    setuptools_parser : SetuptoolsParser = field(default_factory=lambda: SetuptoolsParser())
    metadata_parser : MetadataParser = field(default_factory=lambda: MetadataParser())

    async def parse(self, distribution: Distribution, path: Path, version_hint=None) -> Project:
        children = list(path.iterdir())
        if len(children) == 1 and not ((path / "setup.py").exists() or (path / "pyproject.toml").exists()):
            path = children[0]
        pkg_info = path / "PKG-INFO"
        setup_path = path / "setup.py"
        pyproject_path = path / "pyproject.toml"
        try:
            # if there is a pkg-info file
            # use that + any build dependencies in pyproject.toml
            if pkg_info.exists():
                with open(pkg_info, "rb") as f:
                    project = await self.metadata_parser.parse(distribution, f)
                build_dependencies = list(project.build_dependencies)
                if pyproject_path.exists():
                    build_dependencies.extend(await PyProjectParser.parse_pyproject_build_deps(pyproject_path))
                format = "unknown"
                if setup_path.exists():
                    format = "setuptools"
                elif pyproject_path.exists():
                    format = "pyproject"
                project = replace(
                    project, format=format, 
                    build_dependencies=build_dependencies
                )
                project = Parser.ensure_default_build_deps(project)
                return project
            if setup_path.exists():
                return await self.setuptools_parser.parse(distribution, setup_path)
            if pyproject_path.exists():
                return await self.pyproject_parser.parse(distribution, 
                    pyproject_path, version_hint=version_hint
                )
        except PermissionError:
            raise ParseError(f"Bad permissions: {path}")
        raise ParseError(f"Unable to load project directory: {path}")

# General purpose parser, can handle arbitrary (file or non-file) url
@dataclass
class URLParser:
    sdist_parser: SrcDistParser = field(default_factory=lambda: SrcDistParser())
    metadata_parser : MetadataParser = field(default_factory=lambda: MetadataParser())

    async def parse(self, distribution: Distribution, url: str, res: Resources):
        if url.endswith(".whl"):
            try:
                async with res.fetch(url + ".metadata") as f:
                    proj = await self.metadata_parser.parse(distribution, f)
            except IOError as e: # :( try fetching the full wheel file
                logger.warning("Fetching full wheel file to extract metadata...")
                async with res.fetch(url) as f:
                    proj = None
                    with ZipFile(f) as z:
                        for n in z.namelist():
                            if n.endswith(".dist-info/METADATA"):
                                proj = self.metadata_parser.parse(self, f)
                    if proj is None:
                        raise ParseError("Unable to find metadata")
            proj = replace(proj, format="wheel")
            return proj
        else:
            parsed_url = urllib.parse.urlparse(url)
            filename = parsed_url.path.split("/")[-1]
            file_base = filename.rstrip(".tar.gz").rstrip(".zip")
            name, has_version, version = file_base.rpartition("-")
            if not has_version: version = None
            else:
                try:
                    version = Version(version)
                except InvalidVersion:
                    version = None
                    name = file_base

            logger.info(f"Identifying project information from distribution for {filename}")

            async with res.fetch(url) as f:
                if isinstance(f, Path):
                    # if the resource is a local path,
                    # parse the distribution directly
                    project = await self.sdist_parser.parse(distribution, f, version_hint=version)
                else:
                    # otherwise, extract the resource to a temporary directory
                    with tempfile.TemporaryDirectory(delete=False) as dir:
                        dir = Path(dir)
                        if filename.endswith(".zip"):
                            with zipfile.ZipFile(f) as zf:
                                zf.extractall(dir)
                        elif ".tar" or ".tar.gz" or ".tgz" in filename:
                            with tarfile.open(filename, fileobj=f) as tf:
                                tf.extractall(dir)
                        else:
                            raise RuntimeError(f"Unknown extension in: {filename}")
                        project = await self.sdist_parser.parse(distribution, dir, version_hint=version)
            logger.info(f"Identified source distribution {project.name}=={project.version}")
            return project