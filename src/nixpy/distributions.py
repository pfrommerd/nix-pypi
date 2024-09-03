import json
import urllib.parse
import itertools
import asyncio
import logging
import unearth.finder

from packaging.utils import canonicalize_name
from packaging.version import Version, InvalidVersion
from dataclasses import dataclass, field
from pathlib import Path

from .core import Requirement, Version, Resources, Distribution, URLDistribution

logger = logging.getLogger(__name__)

class DistributionProvider:
    async def find_distributions(self, r: Requirement) -> list[Distribution]:
        # if url source is specified in the requirement,
        # return only that source
        if r.url is not None:
            return [URLDistribution(r.url, None)]
        return []

@dataclass
class CombinedProvider(DistributionProvider):
    providers: list[DistributionProvider]
    union: bool = False # use a union of the providers (vs the first provider that returns a result)

    async def find_distributions(self, r: Requirement) -> list[Distribution]:
        # if the requirement is a URL, return it
        dists = await super().find_distributions(r)
        if dists: return dists
        all_dists = await asyncio.gather(*[p.find_distributions(r) for p in self.providers])
        d = []
        for dists in all_dists:
            d.extend(dists)
            if not self.union and dists:
                break
        return d

class PyPIProvider(DistributionProvider):
    def __init__(self, index_urls=None, find_links=None):
        index_urls = index_urls or ["https://pypi.org/simple/"]
        find_links = find_links or []
        self.finder = unearth.finder.PackageFinder(
            index_urls=index_urls, find_links=find_links,
            target_python=unearth.evaluator.TargetPython(
                # make up a bogus platform so that we
                None, platforms=["linux_allarch"]
            )
        )

    # does the lookup, without caching
    async def find_distributions(self, r: Requirement) -> list[Distribution]:
        # handle url-based requirements
        dist = await super().find_distributions(r)
        if dist: return dist

        results = list(self.finder.find_matches(r))
        # map of version -> best_link we found
        versions = {}
        def proc_result(r):
            version = Version(r.version)
            curr = versions.get(version, None)
            url = r.link.url
            hash = None
            if r.link.hashes:
                if "sha256" in r.link.hashes:
                    hash = r.link.hashes["sha256"]
            src = URLDistribution(url, hash)
            if curr is None or r.link.is_wheel:
                versions[version] = src
        for r in results: proc_result(r)
        order = sorted(versions.keys(), reverse=True)
        versions = [versions[o] for o in order]
        return versions

@dataclass
class CustomProvider(DistributionProvider):
    directory: Path
    _projects: dict[str, dict[Version, Path]] | None = None

    @property
    def projects(self):
        if self._projects is None:
            self._projects = {}
            for p in self.directory.iterdir():
                if p.is_dir():
                    name, has_version, version = p.name.rpartition("-")
                    if not has_version:
                        continue
                    name = canonicalize_name(name)
                    try:
                        version = Version(version)
                    except InvalidVersion:
                        logger.warning(f"Unable to parse version: {version}")
                        continue
                    versions = self._projects.setdefault(name, {})
                    versions[version] = p.resolve()
        return self._projects

    async def find_distributions(self, r: Requirement) -> list[Distribution]:
        # if url source is specified in the requirement,
        # return only that source
        dist = await super().find_distributions(r)
        if dist: return dist

        dists = []
        projects = self.projects.get(canonicalize_name(r.name), {})
        for (version, path) in projects.items():
            if version in r.specifier:
                dists.append(URLDistribution(f"file://{path}"))
        return dists

@dataclass
class CachedProvider(DistributionProvider):
    res: Resources
    provider : DistributionProvider
    cache_path : Path

    async def find_distributions(self, r: Requirement) -> list[Distribution]:
        # if the requirement is a URL, return it
        dist = await super().find_distributions(r)
        if dist: return dist

        # look for the cached sources
        cache_loc = self.cache_path / f"{r.name}.json"
        sources = []
        if cache_loc.exists():
            with open(cache_loc, "r") as f:
                j = json.load(f)
                sources = [Distribution.from_json(s) for s in j]
            sources = [s for s in sources if s.version in r.specifier or s.version is None]
            # if the sources are local, ignore the cache
            if any([s.local for s in sources]):
                sources = []
        # if we can't find the sources, req-query the provider
        if not sources:
            sub_r = Requirement(r.name)
            raw_sources = await self.provider.find_distributions(sub_r)
            # resolve the hashes for any sources
            # that don't have hashes (do this before caching!)
            raw_sources = await asyncio.gather(*[d.resolve(self.res) for d in raw_sources])
            cache_loc.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_loc, "w") as f:
                sources_json = list([s.as_json() for s in raw_sources])
                json.dump(sources_json, f)
            # filter the loaded sources
            sources = [s for s in raw_sources if s.version in r.specifier or s.version is None]
            if not sources:
                logger.warning(f"unable to find sources for: {r}. raw sources: {','.join([str(r) for r in raw_sources])}")
        return sources

