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

import asyncio

import build
import build.util
import build.env
import pyproject_hooks
import concurrent.futures

import tempfile
import zipfile
import tomllib
import tarfile
import urllib.parse

import logging
logger = logging.getLogger(__name__)

class ParseError(RuntimeError): ...

class Parser:
    def post_process(project):
        requirements = tuple(Requirement(str(r)) for r in project.requirements)
        build_requirements = tuple(Requirement(str(r)) for r in project.build_requirements)
        for r in requirements:
            r.name = canonicalize_name(r.name)
        for r in build_requirements:
            r.name = canonicalize_name(r.name)

        return replace(project,
            name=canonicalize_name(project.name),
            requirements=requirements,
            build_requirements=build_requirements
        )

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

    async def parse(self, distribution: Distribution, toml_path : Path, version_hint : str | None = None) -> Project:
        with open(toml_path, "r") as f:
            data = PyProjectParser.parse_toml(f.read(), toml_path.parent.resolve())
        project = data.get("project", None)
        if project is None:
            raise ParseError(f"No project entry in pyproject.toml: {toml_path}")
        name = project.get("name", None)
        if name is None: raise ParseError("No name entry in pyproject.toml")
        version = project.get("version", None)
        version = Version(version) if version is not None else version_hint
        if version == Version("0.0.0"): version = version_hint
        if version is None: raise ParseError("Unable to determine pyproject version")
        req_python = None
        if "dependencies" in project.get("dynamic", []):
            raise ParseError("Dynamic dependencies are not supported...falling back.")
        try:
            deps = tuple(Requirement(r) for r in project.get("dependencies", []))
            # get the build dependencies...
            build_deps = tuple(Requirement(r) for r in data.get("build-system", {}).get("requires", [
                "setuptools>=70", "wheel>=0.43"
            ]))
        except InvalidRequirement as e:
            raise ParseError(e)
        project = Project(
            name, version,
            "pyproject",
            req_python, distribution,
            deps,  build_deps
        )
        return Parser.post_process(project)
    
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
class MetadataParser:
    def parse_data(self, distribution: Distribution, file: IO | EmailMessage, version_hint : Version | None = None) -> Project:
        if hasattr(file, "get") and hasattr(file, "get_all"):
            msg = file
        else:
            p = BytesParser()
            msg = p.parse(file, headersonly=True)
        name = msg.get("Name", None)
        if name is None:
            raise ParseError(f"No name in: {msg}")
        version = msg.get("Version", None)
        try:
            version = Version(version) if version is not None else version_hint
            if version == Version("0.0.0"): version = version_hint
            if version is None:
                raise ParseError(f"No version in: {msg}")
            deps = msg.get_all("Requires-Dist", [])
            deps = tuple(Requirement(r) for r in deps)
            req_python = msg.get("Requires-Python")
            req_python = SpecifierSet(req_python) if req_python else None
        except InvalidVersion as e:
            raise ParseError(e)
        except InvalidRequirement as e:
            raise ParseError(e)

        project = Project(
            name, version, "metadata",
            req_python, distribution,
            deps, ()
        )
        project = Parser.post_process(project)
        return project
    
    async def parse(self, distribution: Distribution, file: IO, version_hint : Version | None = None) -> Project:
        return self.parse_data(distribution, file, version_hint)

# Will parse a distribution distribution
@dataclass
class SrcDistParser:
    pyproject_parser : PyProjectParser = field(default_factory=lambda: PyProjectParser())
    metadata_parser : MetadataParser = field(default_factory=lambda: MetadataParser())
    executor : concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    async def parse(self, distribution: Distribution, path: Path, version_hint=None) -> Project:
        children = list(path.iterdir())
        if len(children) == 1 and not ((path / "setup.py").exists() or (path / "pyproject.toml").exists()):
            path = children[0]
        pkg_info = path / "PKG-INFO"
        # if the source distribution defines a nix expression, use that instead!
        nix_path = path / "default.nix"
        pyproject_path = path / "pyproject.toml"
        project = None
        try:
            # if there is a pkg-info file use that + any build dependencies in pyproject.toml
            if pkg_info.exists() and not version_hint:
                with open(pkg_info, "rb") as f:
                    metadata_project = await self.metadata_parser.parse(distribution, f)
                    version_hint = metadata_project.version
            if pyproject_path.exists():
                try:
                    project = await self.pyproject_parser.parse(distribution, 
                        pyproject_path, version_hint=version_hint
                    )
                except ParseError as _: pass
            if project is None:
                # use "build" as a fallback
                def task():
                    try:
                        with build.env.DefaultIsolatedEnv() as env:
                            builder = build.ProjectBuilder.from_isolated_env(
                                env,
                                path,
                                runner=pyproject_hooks.quiet_subprocess_runner,
                            )
                            build_requires = []
                            build_requires.extend(builder.build_system_requires)
                            env.install(build_requires)
                            has_setuptools = any("setuptools" in r for r in build_requires)
                            if has_setuptools: # ensure setuptools is recent enough
                                               # that the "legacy backend" is available
                                env.install(["setuptools>=70"])
                            extra_requires = builder.get_requires_for_build('wheel')
                            build_requires.extend(extra_requires)
                            env.install(extra_requires)
                            metadata = build.util._project_wheel_metadata(builder)
                            project = self.metadata_parser.parse_data(distribution, metadata)
                            build_requires = tuple(Requirement(r) for r in build_requires)
                            project = replace(project,
                                build_requirements=build_requires
                            )
                            project = Parser.post_process(project)
                            return project
                    except build.BuildBackendException as e:
                        raise ParseError(f"Unable to build project: {e}")

                io_loop = asyncio.get_event_loop()
                project = await io_loop.run_in_executor(self.executor, task)
        except PermissionError:
            raise ParseError(f"Bad permissions: {path}")
        # use setuptools to build the project even if pyproject.toml is present
        if pyproject_path.exists():
            project = replace(project, format="pyproject")
        if nix_path.exists():
            project = replace(project, format="nix")
        if project is None:
            raise ParseError(f"Unable to load project directory: {path}")
        return project

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
                    with zipfile.ZipFile(f) as z:
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

            logger.debug(f"Identifying project information from distribution for {filename}")

            async with res.fetch(url) as f:
                if isinstance(f, Path):
                    # if the resource is a local path,
                    # parse the distribution directly
                    project = await self.sdist_parser.parse(distribution, f, version_hint=version)
                else:
                    # otherwise, extract the resource to a temporary directory
                    td = tempfile.TemporaryDirectory(delete=False)
                    with td as dir:
                        path = Path(dir)
                        if filename.endswith(".zip"):
                            with zipfile.ZipFile(f) as zf:
                                zf.extractall(path)
                        elif ".tar" or ".tar.gz" or ".tgz" in filename:
                            try:
                                with tarfile.open(filename, fileobj=f) as tf:
                                    tf.extractall(path)
                            except tarfile.ReadError as e:
                                raise ParseError(f"Bad tarfile: {e}")
                        else:
                            raise RuntimeError(f"Unknown extension in: {filename}")
                        try:
                            project = await self.sdist_parser.parse(distribution, path, version_hint=version)
                        except ParseError as e:
                            raise e
                        # cleanup if no error
                    td.cleanup()
            logger.debug(f"Identified source distribution {project.name}=={project.version}")
            return project