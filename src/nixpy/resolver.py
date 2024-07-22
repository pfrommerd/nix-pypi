from dataclasses import dataclass

from resolvelib.providers import AbstractProvider

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version    

from .core import Project, Target, Recipe

from threading import Event

import json
import functools
import asyncio
import concurrent.futures
import resolvelib
import logging

logger = logging.getLogger(__name__)

class ResolveProvider(AbstractProvider):
    def __init__(self, io_loop, provider,
                constraints : list[Target] | None,
                preferences : list[Target] | None):
        super().__init__()
        self._provider = provider
        self._io_loop = io_loop
        self.constraints = { t.name : t for t in constraints} if constraints is not None else {}
        self.preferences = { (t.name, t.version) for t in preferences} if preferences is not None else set()

    def identify(self, requirement_or_candidate):
        return canonicalize_name(requirement_or_candidate.name)

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
        candidates = [Target(p, set()) for p in projects]
        candidates_fmt = ", ".join([str(p.version) for p in projects])
        logger.info(f"found targets {identifier}=={candidates_fmt}")
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
        if canonicalize_name(requirement.name) != candidate.name:
            return False
        return candidate.version in requirement.specifier

    def get_dependencies(self, candidate):
        return candidate.dependencies

class Resolver:
    def __init__(self, project_provider):
        self.project_provider = project_provider
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    
    async def resolve_environment(self, 
                requirements: list[Requirement], *,
                constraints: list[Target] | None = None,
                preferences: list[Target] | None = None
            ) -> list[Target]:
        io_loop = asyncio.get_event_loop()
        resolver = resolvelib.Resolver(
            ResolveProvider(io_loop, self.project_provider, constraints, preferences), resolvelib.BaseReporter()
        )
        def task():
            return resolver.resolve(requirements, max_rounds=1000)
        result = await io_loop.run_in_executor(self.executor, task)
        return list(result.mapping.values())

    async def resolve_recipes(self, requirements: list[Requirement]):
        main_targets = await self.resolve_environment(requirements)
        main_env = {t.name : t for t in main_targets}

        # create recipes!
        recipe_queue = list(main_targets)
        selected_targets = {t.id for t in recipe_queue}
        recipes = {}

        async def resolve_build_environment(target):
            requirements = target.dependencies + target.build_dependencies
            # prefer targets for which we intend to build recipes
            preferences = list([r.target for r in recipes.values()])
            results = await self.resolve_environment(
                requirements, preferences=preferences
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
        env = {t.id for t in main_targets}
        main_recipes = {id: r for id, r in recipes.items() if id in env}
        build_recipes = {id: r for id, r in recipes.items() if id not in env}
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