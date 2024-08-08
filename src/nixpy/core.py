from dataclasses import dataclass, field, replace
from pathlib import Path

from functools import cached_property
from zipfile import ZipFile

from packaging.requirements import Requirement, SpecifierSet, InvalidRequirement
from packaging.utils import canonicalize_name
from packaging.markers import Environment as SystemEnvironment
from unearth.evaluator import LinkMismatchError, Version
from string import Template

from typing import Sequence, Any

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

DistributionProvider = Any

@dataclass(frozen=True)
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


@dataclass(frozen=True)
class Project:
    name: str
    version: Version
    format: str
    req_python: SpecifierSet | None
    distribution: Distribution

    requirements: Sequence[Requirement]
    build_requirements: Sequence[Requirement]

    def as_json(self):
        json = {
            "name": self.name,
            "version": str(self.version),
            "format": self.format,
            "req_python": str(self.req_python) if self.req_python is not None else None,
            "distribution": self.distribution.as_json(),
            "requirements": sorted([str(r) for r in self.requirements]),
            "build_requirements": sorted([str(r) for r in self.build_requirements]),
        }
        return json
    
    @staticmethod
    def from_json(proj):
        return Project(proj["name"], Version(proj["version"]), proj["format"],
            SpecifierSet(proj["req_python"]) if proj["req_python"] is not None else None, 
            Distribution.from_json(proj["distribution"]),
            tuple(Requirement(r) for r in proj["requirements"]),
            tuple(Requirement(r) for r in proj["build_requirements"]),
        )

@dataclass
class ProjectProvider:
    res: Resources
    distributions: DistributionProvider
    # a cache location (if set to None, not used)
    # maps sources -> parsed projects
    project_cache_dir : Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "project-cache")
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
        for p in projects:
            loaded_versions[p.version] = p
        return projects

@dataclass(frozen=True)
class SystemInfo:
    python_version: Sequence[int]
    nix_platform: str

    def as_json(self):
        return {
            "python_version": self.python_version,
            "nix_platform": self.nix_platform
        }
    
    @staticmethod
    def from_json(j):
        return SystemInfo(tuple(j["python_version"]), j["nix_platform"])

    @cached_property
    def python_environment(self) -> SystemEnvironment:
        implementation_version = ".".join(str(i) for i in self.python_version)
        implementation_name = "cpython"
        platform_implementation = "CPython"
        python_full_version = ".".join(str(i) for i in self.python_version)
        python_version = ".".join(str(i) for i in self.python_version[:2])

        arch, os = self.nix_platform.split("-")
        if arch == "x86_64":
            platform_machine = "x86_64"
        elif arch == "aarch64":
            platform_machine = "arm64"
        elif arch == "powerpc64le":
            platform_machine = "ppc64le"
        else: raise ValueError(f"Unrecognized architecture: {arch}")

        if os == "linux":
            platform_system = "Linux"
            sys_platform = "linux"
            os_name = "posix"
            platform_version = "#1 SMP Wed Sep 23 05:08:15 EDT 2020"
        elif os == "darwin":
            platform_system = "Darwin"
            platform_version = "Darwin Kernel Version 23.2.0: Wed Nov 15 21:55:06 PST 2023; root:xnu-10002.61.3~2/RELEASE_ARM64_T6020'",
            sys_platform = "darwin"
            os_name = "posix"
        else:
            raise ValueError(f"Unrecognized os: {os}")

        return SystemEnvironment(
            python_full_version=python_full_version,
            python_version=python_version,
            implementation_version=implementation_version,
            implementation_name=implementation_name,

            platform_system=platform_system,
            platform_version=platform_version,
            platform_machine=platform_machine,
            platform_implementation=platform_implementation,
            sys_platform=sys_platform,
            os_name=os_name
        )

# A candidate is a project
# with a set of extras and some
# associated system information.

@dataclass(frozen=True)
class Candidate:
    project: Project
    with_extras: Sequence[str]
    system: SystemInfo

    @property
    def name(self) -> str:
        return self.project.name

    @property
    def version(self) -> Version:
        return self.project.version

    @cached_property
    def evaluated_requirements(self) -> list[Requirement]:
        return list(self._get_requirements())

    @cached_property
    def evaluated_build_requirements(self) -> list[Requirement]:
        return list(self._get_build_requirements())
    
    @staticmethod
    def _marker_satisfies(marker, env, extras):
        if marker is None:
            return True
        env["extra"] = ""
        if marker.evaluate(env):
            return True
        for e in extras:
            env["extra"] = e
            if marker.evaluate(env):
                return True
        return False

    def _get_requirements(self):
        extras = set(self.with_extras) if self.with_extras else {""}
        yield from Candidate._compute_requirements(self.name, 
            self.project.requirements, self.system.python_environment, extras
        )

    def _get_build_requirements(self):
        extras = self.with_extras if self.with_extras else [""]
        yield from Candidate._compute_requirements(self.name, 
            self.project.build_requirements, self.system.python_environment, extras
        )
    
    @staticmethod
    def _compute_requirements(own_name, requirements, env, extras):
        env = dict(env)
        # collect all of the extras
        # by self-requirements
        while True:
            old_extras = extras
            for r in requirements:
                if r.name == own_name and Candidate._marker_satisfies(r.marker, env, extras):
                    extras = extras.union(r.extras)
            if old_extras == extras:
                break
        for r in requirements:
            # exclude self-requirements from the final requirements list
            if r.name == own_name: continue
            if Candidate._marker_satisfies(r.marker, env, extras):
                yield r

    def as_json(self):
        return {
            "project": self.project.as_json(),
            "with_extras": list(sorted(self.with_extras)),
            "system": self.system.as_json()
        }
    
    @staticmethod
    def from_json(j) -> "Target":
        return Candidate(
            project=Project.from_json(j["project"]),
            system=SystemInfo.from_json(j["system"]),
            with_extras=frozenset(j["with_extras"])
        )

# A target is a candidate
# instantiated with a set of dependencies
# and build dependencies.
@dataclass(frozen=True)
class Target:
    candidate: Candidate
    dependencies: Sequence[str] # the target IDs to depend on
    build_dependencies: Sequence[str] # the target IDs to build-depend on

    @property
    def id(self) -> str:
        s = json.dumps(self.as_json(), sort_keys=True)
        hash = hashlib.sha256()
        hash.update(s.encode("utf-8"))
        hash = hash.hexdigest()
        id = f"{self.name}-{self.version}-{hash}"
        return id
    
    @property
    def hash(self) -> str:
        s = json.dumps(self.as_json(), sort_keys=True)
        hash = hashlib.sha256()
        hash.update(s.encode("utf-8"))
        hash = hash.hexdigest()
        return hash

    @property
    def project(self) -> Project:
        return self.candidate.project

    @property
    def name(self) -> str:
        return self.project.name
    
    @property
    def version(self) -> Version:
        return self.project.version
    
    @property
    def distribution(self) -> Distribution:
        return self.project.distribution
    
    def as_json(self):
        return {
            "candidate": self.candidate.as_json(),
            "dependencies": sorted(self.dependencies),
            "build_dependencies": sorted(self.build_dependencies)
        }

    @staticmethod
    def from_json(j):
        return Target(
            candidate=Candidate.from_json(j["candidate"]),
            dependencies=tuple(j["dependencies"]),
            build_dependencies=tuple(j["build_dependencies"])
        )