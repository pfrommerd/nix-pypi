from dataclasses import dataclass, field
from pathlib import Path

from functools import cached_property
from zipfile import ZipFile

from packaging.requirements import Requirement, SpecifierSet, InvalidRequirement
from packaging.utils import canonicalize_name
from unearth.evaluator import LinkMismatchError, Version
from string import Template

from typing import Generator, IO

from .resources import Resources

import json
import hashlib
import packaging.utils
import unearth.utils
import urllib.parse
import tempfile
import asyncio
import logging

import time

START_TIME = time.time()

logger = logging.getLogger(__name__)

class Distribution:
    @staticmethod
    def from_json(r):
        if r.get("type", None) == "url":
            return URLDistribution.from_json(r)
        else: raise ValueError(f"Unexpected source type {r['type']}")

@dataclass
class URLDistribution(Distribution):
    url: str
    # if known, if unknown is blank
    content_hash: str | None = None

    # Tries to determine the version
    # from the name, might be None if unable
    # to determine
    @cached_property
    def version(self) -> Version | None:
        if self.is_wheel:
            _, ver, _, _ = packaging.utils.parse_wheel_filename(self.filename)
            return ver
        else:
            base = self.filename
            # get rid of the archive extension, if one exists
            for a in unearth.utils.ARCHIVE_EXTENSIONS:
                if base.endswith(a):
                    base = base[:-len(a)]
                    break
            pkg, has_version, version = base.rpartition("-")
            if not has_version:
                return None
            try:
                Version(version)
            except unearth.evaluator.InvalidVersion as e:
                return None
            return Version(version)

    @cached_property
    def parsed_url(self):
        return urllib.parse.urlparse(self.url)

    @property
    def cache_key(self) -> str:
        if self.content_hash is None:
            digest = hashlib.sha256((f"{START_TIME}:{self.url}").encode("utf-8"))
            digest = digest.hexdigest()
            # This url cannot be cached!
            return f"{self.filename}-{digest}"
        else:
            return f"{self.filename}-{self.content_hash}"

    @property
    def filename(self) -> str:
        return self.parsed_url.path.split("/")[-1]

    @property
    def local(self) -> bool:
        return self.parsed_url.scheme == "file"

    @property
    def is_wheel(self) -> bool:
        return self.filename.endswith(".whl")
    
    def as_json(self):
        return {"type": "url", "url": self.url, "sha256": self.content_hash}

    @staticmethod
    def from_json(r):
        return URLDistribution(r["url"], r["sha256"])
    
    async def resolve(self, res: Resources) -> Distribution:
        if self.content_hash is None:
            async with res.fetch(self.url) as f:
                # if we successfully fetched the url
                # and it is a file object (not a local directory)
                if f and not isinstance(f, Path):
                    hash = hashlib.file_digest(f, "sha256").hexdigest()
                    return URLDistribution(self.url, hash)
        return self

    async def parse(self, res: Resources) -> "Project":
        from .parser import URLParser
        return await URLParser().parse(self, self.url, res)


@dataclass
class Project:
    name: str
    version: Version
    format: str
    req_python: SpecifierSet | None
    distribution: Distribution

    dependencies: list[Requirement]
    build_dependencies: list[Requirement]

    def as_json(self):
        json = {
            "name": self.name,
            "version": str(self.version),
            "format": self.format,
            "req_python": str(self.req_python) if self.req_python is not None else None,
            "distribution": self.distribution.as_json(),
            "dependencies": sorted([str(r) for r in self.dependencies]),
            "build_dependencies": sorted([str(r) for r in self.build_dependencies]),
        }
        return json
    
    @staticmethod
    def from_json(proj):
        return Project(proj["name"], Version(proj["version"]), proj["format"],
            SpecifierSet(proj["req_python"]) if proj["req_python"] is not None else None, 
            Distribution.from_json(proj["distribution"]),
            [Requirement(r) for r in proj["dependencies"]],
            [Requirement(r) for r in proj["build_dependencies"]],
        )

@dataclass
class ProjectProvider:
    res: Resources
    distributions: "DistributionProvider"
    # a cache location (if set to None, not used)
    # maps sources -> parsed projects
    project_cache_dir : Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "project-cache")
    # extra build dependencies for project (name, version) tuples
    extra_build_dependencies : dict[tuple[str, Version], Requirement] = field(default_factory=dict)
    loaded_projects : dict[str, dict[Version, Project]] = field(default_factory=dict)

    async def _project(self, d: Distribution):
        from .parser import ParseError
        cache_entry = None
        # lock-in the distribution information (i.e. the source tarball hash)
        d = await d.resolve(self.res)
        if self.project_cache_dir is not None and d.cache_key is not None:
            cache_entry = self.project_cache_dir / f"{d.cache_key}.json"
            if cache_entry.exists():
                with open(cache_entry, "r") as f:
                    j = json.load(f)
                    if j is None: return None
                    return Project.from_json(j)
        try:
            project = await d.parse(self.res)
        except ParseError as e:
            project = None
            logger.warning(f"failed to resolve distribution information: {e}")

        if cache_entry is not None:
            cache_entry.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_entry, "w") as f:
                json.dump(project.as_json() if project is not None else None, f)
        return project

    async def find_projects(self, r: Requirement, latest_if_no_spec: bool = True):
        loaded_versions = self.loaded_projects.setdefault(r.name, {})
        projects = [p for p in loaded_versions.values() if p.version in r.specifier]
        if projects:
            return projects
        srcs = await self.distributions.find_distributions(r)
        # if no specifier, just return the latest
        # version so that we don't waste time solving
        # for every possible version of everything!
        if not r.specifier:
            srcs = [srcs[0]]
        projects = await asyncio.gather(*[self._project(s) for s in srcs])
        # filter the projects again, as the distributions
        # might have been overly broad
        projects = [p for p in projects if p is not None and p.version in r.specifier]
        def map_project(p):
            k = (p.name, p.version)
            if k in self.extra_build_dependencies:
                p = replace(p, build_dependencies=p.build_dependencies + self.extra_build_dependencies[k])
            return p
        projects = [map_project(p) for p in projects]
        for p in projects:
            loaded_versions[p.version] = p
        return projects

# A target is a project with a set of extras
@dataclass
class Target:
    project: Project
    with_extras: set[str]
    # The evaluated dependencies, build_dependencies
    _dependencies: list[Requirement] | None = None
    _build_dependencies: list[Requirement] | None = None

    @property
    def id(self) -> str:
        s = json.dumps(self.as_json(), sort_keys=True)
        hash = hashlib.sha256()
        hash.update(s.encode("utf-8"))
        hash = hash.hexdigest()
        id = f"{self.name}-{self.version}-{hash}"
        return id

    @property
    def name(self) -> str:
        return self.project.name
    
    @property
    def version(self) -> Version:
        return self.project.version
    
    @property
    def req_python(self) -> SpecifierSet | None:
        return self.project.req_python
    
    @property
    def distribution(self) -> Distribution:
        return self.project.distribution

    @property
    def dependencies(self) -> list[Requirement]:
        if self._dependencies is None:
            self._dependencies = list(self._get_dependencies())
        return self._dependencies

    @property
    def build_dependencies(self):
        if self._build_dependencies is None:
            self._build_dependencies = list(self._get_build_dependencies())
        return self._build_dependencies

    def _get_dependencies(self):
        extras = self.with_extras if self.with_extras else [""]
        for r in self.project.dependencies:
            if r.marker is None:
                yield r
            else:
                for e in extras:
                    if r.marker.evaluate({"extra": e}):
                        yield r

    def _get_build_dependencies(self):
        extras = self.with_extras if self.with_extras else [""]
        for r in self.project.build_dependencies:
            if r.marker is None:
                yield r
            else:
                for e in extras:
                    if r.marker.evaluate({"extra": e}):
                        yield r
    
    def as_json(self):
        return {
            "project": self.project.as_json(),
            "with_extras": list(sorted(self.with_extras))
        }
    
    @staticmethod
    def from_json(j) -> "Target":
        return Target(
            project=Project.from_json(j["project"]),
            with_extras=set(j["with_extras"])
        )

# represents an completely
# resolved Target, including extras,
# resolved dependencies, and build dependencies
@dataclass
class Recipe:
    target: Target
    # the ids of the recipes
    # for the environemnt to build this target
    env: list[str]

    @property
    def id(self):
        return self.target.id

    @property
    def project(self):
        return self.target.project

    @property
    def name(self):
        return self.project.name

    @property
    def version(self):
        return self.project.version

    @property
    def distribution(self):
        return self.target.project.distribution

    def as_json(self):
        return {
            "target": self.target.as_json(),
            "env": sorted(self.env),
        }

    @staticmethod
    def from_json(j) -> "Recipe":
        return Recipe(
            Target.from_json(j["target"]),
            j["env"], 
        )