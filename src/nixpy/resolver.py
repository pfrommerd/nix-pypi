from dataclasses import dataclass

from resolvelib.providers import AbstractProvider

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version    

from .core import SystemInfo, Candidate, Target, Recipe

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
                raise RuntimeError(f"Unable to satisfy hard-constraint: {target.name}=={target.version}")
            return [target]

        logger.info(f"resolving {requirement}")

        projects = self._find_projects(requirement)
        # populate the targets
        candidates = [Candidate(p, extras, self.system_info) for p in projects]
        candidates_fmt = ", ".join([str(p.version) for p in projects])
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
        return candidate.version in requirement.specifier

    def get_dependencies(self, candidate):
        return candidate.dependencies


# A build candidate is a candidate
# with all dependencies resolved (but not build dependencies)
@dataclass(frozen=True)
class BuildCandidate:
    candidate: Candidate
    dependencies: list[Candidate]

    @staticmethod
    def from_env(candidate: Candidate, env: dict[str: Candidate]):
        pass

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
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    
    async def resolve_candidates(self,
                system_info: SystemInfo,
                requirements: list[Requirement], *,
                constraints: list[Candidate] | None = None,
                preferences: list[Candidate] | None = None
            ) -> dict[str, Candidate]:
        io_loop = asyncio.get_event_loop()
        resolver = resolvelib.Resolver(
            ResolveProvider(io_loop, self.python_version, 
                self.project_provider, constraints, preferences), resolvelib.BaseReporter()
        )
        def task():
            return resolver.resolve(requirements, max_rounds=1000)
        result = await io_loop.run_in_executor(self.executor, task)
        env = list(result.mapping.values())
        return {c.name : c for c in env}

    async def resolve_environment(self, system: SystemInfo, requirements: list[Requirement]):
        main_env_candidates = await self.resolve_environment(system, requirements)
        # Lock dependencies for everything in the main environment

        resolve_queue = [BuildCandidate.from_env(c, main_env_candidates) for c in main_env_candidates.values()]
        resolving = set(resolve_queue)
        # map from BuildCandidate to dict[str, BuildCandidate] of 
        # resolved environments
        resolved = {}

        async def resolve_build_environment(build_candidate):
            all_deps = build_candidate.dependencies + build_candidate.build_dependencies
            env = await self.resolve_candidates(
                system, all_deps
            )
            # convert to BuildCandidates
            env = { k: BuildCandidate.from_env(c, env) for k,c in env.items() }
            resolved[build_candidate] = env
            for n in env.values():
                if n not in resolving:
                    resolve_queue.add(n)
                    resolving.add(n)
        # resolve everything!
        await asyncio.gather()
        # TODO: test for (and break!) cycles 
        # or the next step will hang forever
        async def resolve_target(candidate, env):
            pass

        target_futures = {}
        recipe_queue = list(main_targets.values())
        selected_targets = {t.id for t in recipe_queue}
        recipes = {}

        async def resolve_build_environment(target):
            requirements = target.build_dependencies + target.dependencies
            # prefer the same dependencies as the main environment
            preferences = []
            if target.id in main_target_ids:
                preferences = [main_targets[t.name] for t in target.dependencies]
            results = await self.resolve_environment(
                requirements, preferences=preferences,
            )
            # set the recipe dependencies/build dependencies...
            recipe = Recipe(target,
                [r.id for r in results]
            )
            recipes[target.id] = recipe
            # add any requirements if they need
            # to be added ot the selected targets
            for target in results:
                if target.id not in selected_targets:
                    recipe_queue.append(target)
                    selected_targets.add(target.id)
            return recipe

        # go through the queue!
        while recipe_queue:
            r = recipe_queue.pop()
            dep_requirements = ",".join([f"{r.name}{r.specifier}" for r in r.dependencies + r.build_dependencies])
            logger.info(f"Resolving build environment for {r.name}=={r.version} ({dep_requirements})")
            r = await resolve_build_environment(r)
        
        # split all of the recipes based on whether they
        # are part of the original main environment
        main_recipes = {id: r for id, r in recipes.items() if id in main_target_ids}
        build_recipes = {id: r for id, r in recipes.items() if id not in main_target_ids}
        return main_recipes, build_recipes

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