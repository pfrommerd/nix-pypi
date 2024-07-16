from dataclasses import dataclass

from resolvelib.providers import AbstractProvider

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version    

from .core import Project

from threading import Event

import functools
import asyncio
import concurrent.futures
import resolvelib

@dataclass
class Candidate:
    project : Project
    with_extras : set[str]

    @property
    def name(self):
        return self.project.name

    @property
    def version(self):
        return self.project.version

class ResolveProvider(AbstractProvider):
    def __init__(self, io_loop, provider):
        super().__init__()
        self._provider = provider
        self._io_loop = io_loop

    def identify(self, requirement_or_candidate):
        return canonicalize_name(requirement_or_candidate.name)

    def get_extras_for(self, requirement_or_candidate):
        return tuple(sorted(requirement_or_candidate.extras))

    def get_base_requirement(self, candidate):
        return Requirement("{}=={}".format(candidate.name, candidate.version))

    def get_preference(self, identifier, resolutions, candidates, information):
        return sum(1 for _ in candidates[identifier])
    
    # will offload to the io_loop
    def _find_projects(self, requirement):
        async def task():
            return await self._provider.find_projects(requirement)
        future = asyncio.run_coroutine_threadsafe(task(), self._io_loop)
        return future.result()
    
    def find_matches(self, identifier, requirements, incompatibilities):
        requirements = list(requirements[identifier])

        specifier = functools.reduce(lambda a, b: a & b, [r.specifier for r in requirements])
        extras = set().union(*[r.extras for r in requirements])
        url = functools.reduce(lambda a, b: a or b, [r.url for r in requirements])
        # build a combined requirement
        requirement = _make_requirement(identifier, extras, specifier, url)

        projects = self._find_projects(requirement)
        candidates = [Candidate(p, set()) for p in projects]
        bad_versions = {c.version for c in incompatibilities[identifier]}
        # find all compatible candidates
        candidates = (
            candidate
            for candidate in candidates if candidate.version not in bad_versions
            and candidate.version in requirement.specifier
        )
        return sorted(candidates, key=attrgetter("version"), reverse=True)

    def is_satisfied_by(self, requirement, candidate):
        if canonicalize_name(requirement.name) != candidate.name:
            return False
        return candidate.version in requirement.specifier

    def get_dependencies(self, candidate):
        return candidate.dependencies

class Resolver:
    def __init__(self, project_provider):
        self.project_provider = project_provider
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

    async def resolve(self, requirements: list[Requirement]):
        io_loop = asyncio.get_event_loop()
        resolver = resolvelib.Resolver(
            ResolveProvider(io_loop, self.project_provider), resolvelib.BaseReporter()
        )
        def task():
            return resolver.resolve(requirements)
        result = await io_loop.run_in_executor(self.executor, task)
        return result

def _make_requirement(identifier, extras, specifier, 
                        url = None, markers = None):
    r = identifier
    if extras:
        formatted_extras = ",".join(extras)
        r = r + f"[{formatted_extras}]"
    if url:
        r = r + f" @ {url}"
        if markers: r = r + " "
    if markers:
        r = r + f"; {markers}"
    return Requirement(r)
