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
            # This url cannot be cached!
            return None
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
    req_python: SpecifierSet | None
    distribution: Distribution

    dependencies: list[Requirement]
    build_dependencies: list[Requirement]

    def as_json(self):
        json = {
            "name": self.name,
            "version": str(self.version),
            "req_python": str(self.req_python) if self.req_python is not None else None,
            "distribution": self.distribution.as_json(),
            "dependencies": [str(r) for r in self.dependencies],
            "build_dependencies": [str(r) for r in self.build_dependencies],
        }
        return json
    
    @staticmethod
    def from_json(proj):
        return Project(proj["name"], Version(proj["version"]),
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

# represents an completely
# resolved Target, including extras,
# resolved dependencies, and build dependencies
@dataclass
class Recipe:
    target: Target
    dependencies: list["Recipe"]
    build_requirements: list["Recipe"]

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