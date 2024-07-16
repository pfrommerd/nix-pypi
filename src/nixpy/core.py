from dataclasses import dataclass
from pathlib import Path

from packaging.requirements import Requirement

from typing import Generator

import hashlib
import aiohttp
import asyncio
import urllib.parse
import resolvelib
import unearth.finder
import tomllib
import contextlib
import tempfile

class Source: pass

@dataclass
class LocalSource(Source):
    path: Path

    @property
    def local(self): return True

@dataclass
class RemoteSource(Source):
    url: str
    # if known, if unknown is blank
    content_hash: str | None = None

    @property
    def local(self): return False

# Represents all of the parsed information
# which can be gained by looking at a particular package
@dataclass
class Project:
    name: str
    version: str
    source : Source
    deps: list[Requirement]
    build_deps: list[Requirement]

    @staticmethod
    def parse_from_pyproject(source: Source, toml_path : Path):
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        project = data["project"]
        deps = [Requirement(r) for r in project.get("dependencies", [])]
        build_deps = [Requirement(r) for r in project.get("build-system", {}).get("requirements", [])]
        feature_deps = {
            k: [Requirement(r) for r in v] for (k,v) in project.get("optional-dependencies", {}).items()
        }
        # add the optional dependencies as marker-conditional dependencies
        return Project(
            project["name"],
            project["version"],
            source, deps, build_deps,
        )

    @staticmethod
    def parse_from_setup_py(source: Source, setup_py: Path):
        raise ValueError("Can't parse setup.py!")
        pass

    @staticmethod
    def parse_from_directory(source: Source, path : Path):
        if (path  / "pyproject.toml").exists():
            return Project.parse_from_pyproject(source, path / "pyproject.toml")
        if (path  / "setup.py").exists():
            return Project.parse_from_setup_py(source, path / "setup.py")
        raise ValueError(f"Unable to parse project metadata: {path}")

class PyPISourceProvider:
    def __init__(self, index_urls):
        self.finder = unearth.finder.PackageFinder(index_urls=index_urls)
    
    async def find_sources(self, r: Requirement) -> list[Source]:
        print(f"Finding {r}")
        result = self.finder.find_matches(r)
        print(result)
        pass

class ProjectsManager:
    def __init__(self, *, tmp_dir = None, src_provider = None):
        tmp_dir = Path(tmp_dir or tempfile.gettempdir())
        self.src_provider = src_provider
        # maps {project_name :  { project_version : project }
        self.projects = {}
        # url hash cache
        self.url_hashes = {}
        self.dl_cache_dir = tmp_dir / "nixpy-dl-cache"
        self.src_cache_dir = tmp_dir / "nixpy-src-cache"
        self.project_cache_dir = tmp_dir / "nixpy-proj-cache"
    
    async def fetch(self, url : str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        self.dl_cache_dir.mkdir(parents=True, exist_ok=True)
        dl_path = self.dl_cache_dir / digest
        if dl_path.exists():
            return dl_path
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise IOError(f"Failed to fetch url {url}")
                with open(dl_path, "wb") as fd:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        fd.write(chunk)

    async def resolve_hash(self, url: str) -> str:
        dl = self.fetch(url)

    @contextlib.asynccontextmanager
    async def use_source(self, src : LocalSource | RemoteSource) -> Generator[None, None, Path]:
        if isinstance(src, LocalSource):
            yield src.path
        elif isinstance(src, RemoteSource):
            path = await self.fetch(src.url)
            yield path

    # find all matches for a given requirement.
    # if already in projects, assumes the lookup has already been done
    async def find_projects(self, r: Requirement) -> list[Project]:
        # if there is a url specified, try that directly
        if r.url is not None:
            url = urllib.parse.urlparse(r.url)
            if url.scheme == "file": src = LocalSource(Path(url.path))
            else: src = RemoteSource(r.url)
            sources = [src]
        elif r.name in self.projects:
            # return all compatible projects 
            # for the given name in the cache
            versions = self.projects[r.name]
            compatible = [p for (v, p) in versions.items() if v.version in r.specifier]
            if compatible:
                return compatible
            sources = []
        # if we can't find anything compatible, query the index
        if not sources and self.src_provider is not None:
            sources = await self.src_provider.find_sources(r)
        elif self.src_provider is None:
            raise RuntimeError("No provider!")
        # resolve the given sources
        projects = await asyncio.gather(*[self.resolve(s) for s in sources])
        return projects

    async def resolve(self, src: Source) -> Project:
        async with self.use_source(src) as path:
            project = Project.parse_from_directory(src, path)
            self.projects.setdefault(project.name, {})[project.version] = project
            return project