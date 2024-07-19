# Contains tools for parsing the project
# information from either binary or distribution distributions

from email.message import EmailMessage
from email.parser import BytesParser

from dataclasses import dataclass, field, replace

from .core import Project, Version, Distribution, Requirement
from .resources import Resources
from packaging.version import InvalidVersion
from packaging.requirements import InvalidRequirement
from packaging.utils import canonicalize_name

from pathlib import Path
from typing import IO
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

@dataclass
class PyProjectParser:
    async def parse(self, distribution: Distribution, toml_path : Path, version_hint : str | None = None) -> Project:
        env = {
            "PROJECT_ROOT": toml_path.parent.resolve(),
            "PWD": toml_path.parent.resolve(),
        }
        with open(toml_path, "r") as f:
            f = Template(f.read())
            f = f.substitute(**env)
            data = tomllib.loads(f)
        project = data.get("project", None)
        if project is None: raise ParseError(f"No project entry in pyproject.toml: {toml_path}")
        name = project.get("name", None)
        if name is None: raise ParseError("No name entry in pyproject.toml")
        version = project.get("version", None)
        version = Version(version) if version is not None else version_hint
        if version is None:
            raise ParseError("Unable to determine pyproject version")
        req_python = None
        deps = [Requirement(r) for r in project.get("dependencies", [])]
        build_deps = [Requirement(r) for r in project.get("build-system", {}).get("requirements", [])]
        feature_deps = {
            k: [Requirement(r) for r in v] for (k,v) in project.get("optional-dependencies", {}).items()
        }
        return Project(
            canonicalize_name(name), version, 
            req_python, distribution,
            deps,  build_deps
        )
    
    async def parse_tool_info(self, toml_path: Path, tool_name : str) -> dict[str, str]:
        env = {
            "PROJECT_ROOT": toml_path.parent.resolve(),
            "PWD": toml_path.parent.resolve(),
        }
        with open(toml_path, "r") as f:
            f = Template(f.read())
            f = f.substitute(**env)
            data = tomllib.loads(f)
        tools = data.get("tool", {})
        return tools.get(tool_name, {})

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
        project = replace(project, 
            build_dependencies=project.build_dependencies + [Requirement("setuptools")]
        )
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
        return Project(
            canonicalize_name(name), Version(version), req_python, distribution,
            deps, []
        )

# Will parse a distribution distribution
@dataclass
class SrcDistParser:
    pyproject_parser : PyProjectParser = field(default_factory=lambda: PyProjectParser())
    setuptools_parser : SetuptoolsParser = field(default_factory=lambda: SetuptoolsParser())

    async def parse(self, distribution: Distribution, path: Path, version_hint=None) -> Project:
        children = list(path.iterdir())
        if len(children) == 1 and not ((path / "setup.py").exists() or (path / "pyproject.toml").exists()):
            path = children[0]
        setup_path = path / "setup.py"
        pyproject_path = path / "pyproject.toml"
        if setup_path.exists():
            return await self.setuptools_parser.parse(distribution, setup_path)
        if pyproject_path.exists():
            return await self.pyproject_parser.parse(distribution, 
                pyproject_path, version_hint=version_hint
            )
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
                    return await self.metadata_parser.parse(distribution, f)
            except IOError as e: # :( try fetching the full wheel file
                logger.warning("Fetching full wheel file to extract metadata...")
                async with res.fetch(url) as f:
                    with ZipFile(f) as z:
                        for n in z.namelist():
                            if n.endswith(".dist-info/METADATA"):
                                return self.metadata_parser.parse(self, f)
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
                    with tempfile.TemporaryDirectory(delete=True) as dir:
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