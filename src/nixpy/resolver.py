from dataclasses import dataclass

from resolvelib.providers import AbstractProvider

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version    

from .core import SystemInfo, Candidate, Target
from typing import Sequence

from threading import Event

import json
import functools
import asyncio
import concurrent.futures
import resolvelib
import logging

logger = logging.getLogger(__name__)

class ResolveProvider(AbstractProvider):
    def __init__(self, io_loop, system_info, provider,
                constraints : list[Candidate] | None,
                preferences : list[Candidate] | None):
        super().__init__()
        self._provider = provider
        self._io_loop = io_loop
        self.system_info = system_info
        self.constraints = { t.name : t for t in constraints} if constraints is not None else {}
        self.preferences = { (t.name, t.version) for t in preferences} if preferences is not None else set()

    def identify(self, requirement_or_candidate):
        return requirement_or_candidate.name

    def get_extras_for(self, requirement_or_candidate):
        return tuple(sorted(requirement_or_candidate.extras))

    def get_base_requirement(self, candidate):
        return Requirement("{}=={}".format(candidate.name, candidate.version))

    def get_preference(self, identifier, resolutions, candidates, information, backtrack_causes):
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

        # if we have a hard constraint,
        # return only the constrained version,
        # if possible
        if identifier in self.constraints:
            target = self.constraints[identifier]
            if not target.version in requirement.specifier or target.version in incompatibilities:
                logger.warning(f"Unable to satisfy hard-constraint: {target.name}=={target.version} with {requirement}")
            return [target]

        logger.info(f"resolving {requirement}")

        projects = self._find_projects(requirement)
        # populate the targets
        candidates = [Candidate(p, tuple(sorted(extras)), self.system_info) for p in projects]
        # candidates_fmt = ", ".join(f"{p.version} ({" ".join(f"{r.name}{r.specifier}" for r in p.requirements)})" for p in projects)
        candidates_fmt = ", ".join(f"{p.version}" for p in projects)
        logger.info(f"found candidates {identifier}=={candidates_fmt}")

        bad_versions = {c.version for c in incompatibilities[identifier]}
        # find all compatible candidates
        candidates = list([
            candidate
            for candidate in candidates if candidate.version not in bad_versions
            and candidate.version in requirement.specifier
        ])
        candidates = sorted(candidates, key=lambda r: r.version, reverse=True)
        if not candidates:
            raise RuntimeError(f"Unable to find candidates for {requirement}")
        # make any preferred candidates first!
        preferred = [c for c in candidates if (c.name, c.version) in self.preferences]
        regular = [c for c in candidates if (c.name, c.version) not in self.preferences]
        return preferred + regular

    def is_satisfied_by(self, requirement, candidate):
        if requirement.name != candidate.name:
            return False
        if requirement.name in self.constraints:
            required_version = self.constraints[requirement.name].version
            return required_version == candidate.version
        return candidate.version in requirement.specifier

    def get_dependencies(self, candidate):
        return candidate.evaluated_requirements

# A build candidate is a candidate
# with all dependencies explicitly resolved 
# (but not build dependencies)
@dataclass(frozen=True)
class BuildCandidate:
    candidate: Candidate
    # dependencies, including transitive dependencies
    # (but not build dependencies!)
    runtime_env: tuple[Candidate]

    @staticmethod
    def from_env(candidate: Candidate, env: dict[str: Candidate]):
        queue = set(d.name for d in candidate.evaluated_requirements)
        deps : dict[str, Candidate] = {}
        while queue:
            c = env[queue.pop()]
            deps[c.name] = c
            for d in c.evaluated_requirements:
                if d.name not in deps:
                    queue.add(d.name)
        deps = tuple(sorted(deps.values(), key=lambda c: c.name))
        return BuildCandidate(candidate, deps)

# An environment is a system_info
# with a map of target_id -> Target
# (including all locked build-dependencies)
@dataclass(frozen=True)
class Environment:
    system_info: SystemInfo
    targets: dict[str, Target]
    env: set[str]

class Resolver:
    def __init__(self, project_provider):
        self.project_provider = project_provider
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
    async def resolve_candidates(self,
                system_info: SystemInfo,
                requirements: list[Requirement], *,
                constraints: list[Candidate] | None = None,
                preferences: list[Candidate] | None = None,
                task_name: str | None = None
            ) -> dict[str, Candidate]:
        io_loop = asyncio.get_event_loop()
        resolver = resolvelib.Resolver(
            ResolveProvider(io_loop, system_info, 
                self.project_provider, constraints, preferences), 
                resolvelib.BaseReporter()
        )
        def task():
            if task_name is not None:
                logger.info(f"Resolving for {task_name}")
            logger.info("Resolving requirements: {}".format(",".join(str(r) for r in requirements)))
            return resolver.resolve(requirements, max_rounds=1000)
        result = await io_loop.run_in_executor(self.executor, task)
        env = list(result.mapping.values())
        return {c.name : c for c in env}

    async def resolve_environment(self, 
                    system: SystemInfo,
                    requirements: list[Requirement]) -> Environment:
        # Lock dependencies for everything in the main environment
        main_candidates = await self.resolve_candidates(system, requirements)

        logger.info("Main environment resolved: {}".format(", ".join(f"{c.name}=={c.version}" for c in main_candidates.values())))

        # map from build_candidate -> task (returning the target)
        resolved = {}
        async def resolve_target(build_candidate : BuildCandidate) -> Target:
            all_requirements = build_candidate.candidate.evaluated_requirements + build_candidate.candidate.evaluated_build_requirements
            # the constraints is the non-build environment
            constraints = build_candidate.runtime_env
            # resolve the build environment, using the specified 
            # non-build dependencies
            env = await self.resolve_candidates(
                system, all_requirements,
                constraints=constraints,
                task_name=build_candidate.candidate.name
            )
            # convert the environment to BuildCandidates
            env = { k: BuildCandidate.from_env(c, env) for k,c in env.items() }

            # resolve the targets for the Build candidates
            tasks = []
            for c in env.values():
                if c.candidate.name == build_candidate.candidate.name:
                    continue
                if c not in resolved:
                    task = asyncio.create_task(resolve_target(c))
                    tasks.append(task)
                    resolved[c] = task
                else:
                    tasks.append(resolved[c])
            env = await asyncio.gather(*tasks)
            # get the name -> target mapping for the build environment
            env = { t.name : t for t in env }
            # return the original candidate
            dependencies = { r.name : env[r.name].id for r in build_candidate.candidate.evaluated_requirements }
            build_dependencies = { r.name : env[r.name].id for r in build_candidate.candidate.evaluated_build_requirements }
            return Target(
                build_candidate.candidate,
                dependencies=tuple(dependencies.values()),
                build_dependencies=tuple(build_dependencies.values())
            )

        for c in main_candidates.values():
            c = BuildCandidate.from_env(c, main_candidates)
            task = asyncio.create_task(resolve_target(c))
            resolved[c] = task

        # the main environment targets
        env = await asyncio.gather(*resolved.values())
        env = set(t.id for t in env)
        # await all of the tasks to get the final targets
        targets = await asyncio.gather(*resolved.values())
        targets = {
            t.id : t for t in targets
        }
        return Environment(
            system, targets, env
        )

def _make_requirement(identifier, extras, specifier, 
                        url = None, markers = None):
    r = identifier
    if extras:
        formatted_extras = ",".join(extras)
        r = r + f"[{formatted_extras}]"
    if specifier is not None:
        r = r + str(specifier)
    if url:
        r = r + f" @ {url}"
        if markers: r = r + " "
    if markers:
        r = r + f"; {markers}"
    return Requirement(r)