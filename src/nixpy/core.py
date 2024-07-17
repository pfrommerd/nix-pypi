from dataclasses import dataclass
from pathlib import Path

from email.message import EmailMessage
from email.parser import BytesParser
from zipfile import ZipFile

from packaging.requirements import Requirement, SpecifierSet, InvalidRequirement
from packaging.utils import canonicalize_name
from unearth.evaluator import LinkMismatchError, Version
from string import Template

from typing import Generator, IO

import glob
import re
import build.util
import subprocess
import tarfile
import zipfile
import logging
import json
import hashlib
import asyncio
import requests
import concurrent.futures
import urllib.parse
import resolvelib
import unearth.finder
import tomllib
import contextlib
import tempfile

logger = logging.getLogger(__name__)

class Source:
    @staticmethod
    def from_json(r):
        if r.get("type") == "local":
            return LocalSource.from_json(r)
        elif r.get("type") == "remote":
            return RemoteSource.from_json(r)
        else: raise ValueError(f"Unexpected source type {r['type']}")

@dataclass
class LocalSource(Source):
    path: Path

    @property
    def local(self): return True

    @property
    def is_wheel(self): return False

    async def load(self, project_manager) -> "Project":
        # untar orunzip if necessary
        if self.path.is_file():
            with tempfile.TemporaryDirectory(delete=False) as dir:
                dir = Path(dir)
                filename = self.path.name
                if filename.endswith(".zip"):
                    with zipfile.ZipFile(path) as zf:
                        zf.extractall(dir)
                elif ".tar" in filename:
                    with tarfile.open(path) as tf:
                        tf.extractall(dir)
                children = list(dir.iterdir())
                if len(children) == 1: dir = children[0]
                project = await Project.load_from_directory(self, dir)
        else:
            return await Project.load_from_directory(self, self.path)

    def as_json(self):
        return {"type": "local", "path": str(self.path.resolve())}
    
    @staticmethod
    def from_json(r):
        return LocalSource(Path(r["path"]))
    
@dataclass
class CustomSource(Source):
    name: str
    version: str

    # Pre-built, so acts like a wheel
    @property
    def is_wheel(self): return True

    # just regurgiate the name, version
    async def load(self, pm) -> "Package":
        return Project(
            self.name,
            Version(self.version), None,
            [], [], self
        )

@dataclass
class RemoteSource(Source):
    url: str
    # if known, if unknown is blank
    content_hash: str | None = None

    @property
    def local(self): return False

    @property
    def is_wheel(self):
        return self.url.endswith(".whl")
    
    def as_json(self):
        return {"type": "remote", "url": self.url, "sha256": self.content_hash}
    
    @staticmethod
    def from_json(r):
        return RemoteSource(r["url"], r["sha256"])
    
    async def _load(self, pm):
        parsed_url = urllib.parse.urlparse(self.url)
        # make the identity the url filename
        filename = parsed_url.path.split("/")[-1]
        # If this is a wheel, fetch the wheel information...
        if self.is_wheel:
            try:
                # read in the metadata
                metadata = await pm.fetch(self.url + ".metadata")
                with open(metadata, "rb") as f:
                    project = await Project.load_from_metadata(self, f)
            except IOError as e: # :( try fetching the full wheel file
                logger.warning("Fetching full wheel file to extract metadata...")
                path = await pm.fetch(self.url)
                with open(path, "rb") as f:
                    project = await Project.load_from_wheel(self, f)
        else:
            # parse the version from the filename, in case it is
            # dynamic in the source (and we don't want to run the full builder)
            file_base = filename.rstrip(".tar.gz").rstrip(".zip")
            name, has_version, version = file_base.rpartition("-")
            if not has_version: version = None
            # if we have a source distribution,
            # extract the source...
            logger.info(f"Identifying project information from source distribution for {filename}")
            try:
                path = await pm.fetch(self.url)
                with tempfile.TemporaryDirectory(delete=False) as dir:
                    dir = Path(dir)
                    if filename.endswith(".zip"):
                        with zipfile.ZipFile(path) as zf:
                            zf.extractall(dir)
                    elif ".tar" in filename:
                        with tarfile.open(path) as tf:
                            tf.extractall(dir)
                    children = list(dir.iterdir())
                    if len(children) == 1: dir = children[0]
                    project = await Project.load_from_directory(self, dir, version_hint=version)
                logger.info(f"Source distribution identified for {file_base}")
            except ProjectError as e:
                logger.error(f"Unable to determine source distribution for {file_base}, marking package as bad.")
                logger.error(e)
                project = None
        return project

    async def load(self, pm) -> "Project":
        content_hash = self.content_hash
        if not content_hash:
            # manually download + hash the file...
            if self.is_wheel:
                logger.warning(f"Fetching full wheel file to compute hash: {self.url} ")
            path = await pm.fetch(self.url)
            with open(path, "rb") as f:
                content_hash = hashlib.file_digest(f, hashlib.sha256).hexdigest()
        src = RemoteSource(self.url, content_hash)
        parsed_url = urllib.parse.urlparse(self.url)
        # make the identity the url filename
        cache_identifier = parsed_url.path.split("/")[-1]
        try:
            info = pm.get_cached_project_info(content_hash, cache_identifier)
            if info is not None: return info
        except ProjectError as e:
            logger.error(e)
            return None
        try:
            project = await self._load(pm)
        except InvalidRequirement as r:
            logger.warning(f"Invalid requirement: {r} for {cache_identifier}")
            project = None
        pm.cache_project_info(content_hash, cache_identifier, project)
        return project

class ProjectError(RuntimeError): ...

# Represents all of the parsed information
# which can be gained by looking at a particular package
@dataclass
class Project:
    name: str
    version: Version
    req_python: SpecifierSet | None
    deps: list[Requirement]
    build_deps: list[Requirement]
    source: Source

    @staticmethod
    async def load_from_pyproject(
                source: Source,
                toml_path : Path, *, 
                version_hint : str | None = None):
        env = {
            "PROJECT_ROOT": toml_path.parent.resolve(),
            "PWD": toml_path.parent.resolve(),
        }
        with open(toml_path, "r") as f:
            f = Template(f.read())
            f = f.substitute(**env)
            data = tomllib.loads(f)
        project = data.get("project", None)
        if project is None: raise ProjectError(f"No project entry in pyproject.toml: {toml_path}")
        name = project.get("name", None)
        if name is None: raise ProjectError("No name entry in pyproject.toml")
        version = project.get("version", version_hint)
        if version is None:
            raise ProjectError("Unable to determine pyproject version")
        req_python = None
        deps = [Requirement(r) for r in project.get("dependencies", [])]
        build_deps = [Requirement(r) for r in project.get("build-system", {}).get("requirements", [])]
        feature_deps = {
            k: [Requirement(r) for r in v] for (k,v) in project.get("optional-dependencies", {}).items()
        }
        # add the optional dependencies as marker-conditional dependencies
        return Project(
            name, Version(version), req_python, deps, 
            build_deps, source
        )

    @staticmethod
    async def load_from_metadata(source: Source, file: IO) -> "Project":
        if hasattr(file, "get") and hasattr(file, "get_all"):
            msg = file
        else:
            p = BytesParser()
            msg = p.parse(file, headersonly=True)
        name = msg.get("Name")
        version = msg.get("Version")
        deps = msg.get_all("Requires-Dist", [])
        deps = list([Requirement(r) for r in deps])
        req_python = msg.get("Requires-Python")
        return Project(
            name, Version(version), req_python, 
            deps, [], source
        )

    @staticmethod
    async def load_from_wheel(source: Source, file : IO) -> "Project":
        with ZipFile(file) as z:
            for n in z.namelist():
                if n.endswith(".dist-info/METADATA"):
                    return await Project.load_from_metadata(self, z.open(n))
        raise ValueError("Metadata not found")

    @staticmethod
    async def load_from_setup_py(source: Source, setup_py: Path):
        cwd = setup_py.parent.resolve()
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
                raise ValueError(f"Can't parse setup.py: {setup_py}\n{msg}")
        else:
            info = match.group(1)
        info = cwd / info
        with open(info, "rb") as f:
            project = await Project.load_from_metadata(source, f)
        project.build_deps.append(Requirement("setuptools"))
        return project

    @staticmethod
    async def load_from_directory(source: Source, path : Path, *, version_hint : str | None = None):
        if (path  / "setup.py").exists():
            return await Project.load_from_setup_py(source, path / "setup.py")
        if (path  / "pyproject.toml").exists():
            return await Project.load_from_pyproject(source, path / "pyproject.toml", version_hint=version_hint)
        raise ProjectError(f"Unable to load project directory: {path}")

    def as_json(self):
        json = {
            "name": self.name,
            "version": str(self.version),
            "req_python": str(self.req_python) if self.req_python is not None else None,
            "deps": [str(r) for r in self.deps],
            "build_deps": [str(r) for r in self.build_deps],
            "source": self.source.as_json()
        }
        return json
    
    @staticmethod
    def from_json(proj):
        return Project(proj["name"], Version(proj["version"]),
            SpecifierSet(proj["req_python"]) if proj["req_python"] is not None else None, 
            [Requirement(r) for r in proj["deps"]],
            [Requirement(r) for r in proj["build_deps"]],
            Source.from_json(proj["source"])
        )

# Allows for source-directory file:// links
class CustomEvaluator(unearth.evaluator.Evaluator):
    def evaluate_link(self, link):
        parsed = urllib.parse.urlparse(link.url)
        # if we have a file, allow raw directories without extensions
        # which can be interpreted as local sources
        if parsed.scheme == "file":
            try:
                base = link.filename
                # get rid of the archive extension, if one exists
                for a in unearth.utils.ARCHIVE_EXTENSIONS:
                    if base.endswith(a):
                        base = base[:-len(a)]
                        break
                pkg, has_version, version = base.rpartition("-")
                pkg = canonicalize_name(pkg)
                if pkg != canonicalize_name(self.package_name):
                    return None
                if not has_version:
                    raise LinkMismatchError("No version in file!")
                try:
                    Version(version)
                except unearth.evaluator.InvalidVersion as e:
                    raise LinkMismatchError("Invalid version!")
                return unearth.evaluator.Package(name=self.package_name, version=version, link=link)
            except LinkMismatchError as e:
                logger.trace(f"Skipping link: {e}")
                return None
        else:
            return super().evaluate_link(link)

class CustomFinder(unearth.finder.PackageFinder):
    def build_evaluator(
                self, package_name: str, allow_yanked: bool = False
            ) -> unearth.evaluator.Evaluator:
        format_control = unearth.finder.FormatControl(
            no_binary=self.no_binary, only_binary=self.only_binary
        )
        return CustomEvaluator(
            package_name=package_name,
            target_python=self.target_python,
            ignore_compatibility=self.ignore_compatibility,
            allow_yanked=allow_yanked,
            format_control=format_control,
            exclude_newer_than=self.exclude_newer_than,
        )

class PyPISourceProvider:
    def __init__(self, index_urls, find_links, cache_dir=None):
        self.finder = CustomFinder(index_urls=index_urls, find_links=find_links)
        self.cache = cache_dir or Path(tempfile.gettempdir()) / "nixpy-find-cache"
        self.cache.mkdir(parents=True, exist_ok=True)
    
    # does the lookup, without caching
    async def _find(self, name) -> list[Source]:
        results = list(self.finder.find_all_packages(name))
        # map of version -> best_link we found
        versions = {}
        def proc_result(r):
            curr = versions.get(r.version, None)
            url = r.link.url
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme != "file":
                hash = None
                if r.link.dist_info_metadata:
                    if "sha256" in r.link.dist_info_metadata:
                        hash = r.link.dist_info_metadata["sha256"]
                src = RemoteSource(url, hash)
                if hash or curr is None:
                    versions[r.version] = src
            else:
                src = LocalSource(Path(parsed.path).resolve())
                versions[r.version] = src
        for r in results: proc_result(r)
        return versions
    
    async def find_sources(self, r: Requirement) -> list[Source]:
        # cache the finder results
        cache_file = self.cache / f"{r.name}.json"
        versions = None
        if cache_file.exists():
            with open(cache_file, "r") as f:
                j = json.load(f)
                versions = {k: Source.from_json(v) for (k,v) in j.items()}
        # if we don't have any viable versions yet, search again
        if not versions:
            versions = await self._find(r.name)
            with open(cache_file, "w") as f:
                j = {k: v.as_json() for (k,v) in versions.items()}
                json.dump(j, f)
        # filter versions by requirement compatibility
        versions = {k: v for (k,v) in versions.items() if k in r.specifier}
        order = sorted(versions.keys(), key=lambda x: Version(x), reverse=True)
        final_results = [versions[o] for o in order]
        if not final_results:
            logger.warning(f"Unable to find sources for: {r}")
        return final_results

class ProjectsManager:
    def __init__(self, *, tmp_dir = None, src_provider = None):
        tmp_dir = Path(tmp_dir or tempfile.gettempdir())
        self.src_provider = src_provider
        # maps {project_name :  { project_version : project }
        self.projects = {}
        # the request pool executor
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        # url hash cache
        self.url_hashes = {}
        self.dl_cache_dir = tmp_dir / "nixpy-dl-cache"
        self.src_cache_dir = tmp_dir / "nixpy-src-cache"
        self.project_cache_dir = tmp_dir / "nixpy-proj-cache"
    
    async def fetch(self, url : str) -> Path:
        # compute the cache path...
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        filename = urllib.parse.urlparse(url).path.split("/")[-1]
        filename = digest + "-" + filename
        self.dl_cache_dir.mkdir(parents=True, exist_ok=True)
        dl_path = self.dl_cache_dir / filename
        if dl_path.exists():
            return dl_path

        vcs, vcs_url = None, None
        if url.startswith("git+"):
            vcs = "git"
            vcs_url = url[len("git+"):]

        if vcs is None:
            io_loop = asyncio.get_event_loop()
            def do_fetch():
                    r = requests.get(url, allow_redirects=True)
                    with open(dl_path, "wb") as f:
                        f.write(r.content)
            await io_loop.run_in_executor(self.executor, do_fetch)
        else: raise RuntimeError("Unable to use VCS")
        return dl_path
        
    def get_cached_project_info(self, content_hash : str, ident : str):
        loc = self.project_cache_dir / (f"{ident}-{content_hash}.json")
        if loc.exists():
            with open(loc, "r") as f:
                j = json.load(f)
                if j is None: raise ProjectError(f"Bad cache entry for {ident}-{content_hash}")
                return Project.from_json(j)
        else:
            logger.debug(f"Cache miss for {ident}-{content_hash}")
            return None

    def cache_project_info(self, content_hash : str, ident: str, project : Project):
        loc = self.project_cache_dir / (f"{ident}-{content_hash}.json")
        self.project_cache_dir.mkdir(parents=True, exist_ok=True)
        with open(loc, "w") as f:
            json.dump(project.as_json() if project is not None else None, f)
    
    def add_project(self, p: Project):
        versions = self.projects.setdefault(p.name, {})
        versions.setdefault(p.version, p)
    
    async def _find_projects(self, r: Requirement) -> list[Project]:
        sources = []
        if r.url is not None:
            url = urllib.parse.urlparse(r.url)
            if not url.scheme:
                raise ValueError(f"Invalid url scheme: {r.url}")
            if url.scheme == "file": src = LocalSource(Path(url.path))
            else: src = RemoteSource(r.url)
            sources = [src]
        elif r.name in self.projects:
            # return all compatible projects 
            # for the given name in the cache
            versions = self.projects[r.name]
            compatible = [p for (v, p) in versions.items() if v in r.specifier]
            if compatible:
                return compatible
        # if we can't find anything compatible, query the index
        if not sources and self.src_provider is not None:
            sources = await self.src_provider.find_sources(r)
        elif self.src_provider is None:
            raise RuntimeError("No provider!")

        # If there is no specifier, take the only best version
        # so we don't waste our time resolving other things...
        if not r.specifier and len(sources) > 0:
            for s in sources:
                src = await s.load(self)
                if src is not None: return [src]
            return []

        # resolve the given sources
        projects = await asyncio.gather(*[s.load(self) for s in sources])
        projects = list([p for p in projects if p is not None])
        return projects

    # find all matches for a given requirement.
    # if already in projects, assumes the lookup has already been done
    async def find_projects(self, r: Requirement) -> list[Project]:
        # will find the projects, add them to the cache
        # associated with this project manager
        projects = await self._find_projects(r)
        for p in projects:
            self.add_project(p)
        if not projects:
            logger.warning(f"Unable to find projects for: {r}, sources: {sources}")
        return projects