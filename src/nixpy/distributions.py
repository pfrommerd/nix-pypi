import unearth.finder
import unearth.evaluator
import json
import tempfile
import urllib.parse
import itertools
import asyncio
import logging

from packaging.utils import canonicalize_name
from dataclasses import dataclass, field
from pathlib import Path

from .core import Requirement, Version, Resources, Distribution, URLDistribution

from unearth.evaluator import LinkMismatchError

logger = logging.getLogger(__name__)

class DistributionProvider:
    async def find(self, r: Requirement, res: Resources) -> list[Distribution]:
        ...

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
    def __init__(self, *args, extra_links=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra_links = [unearth.evaluator.Link(l) for l in extra_links]

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
    
    # override the _find_packages to include the extra links
    # if they are specified
    def _find_packages(self, package_name, allow_yanked: bool = False):
        packages = super()._find_packages(package_name, allow_yanked)
        if not self.extra_links:
            return packages
        evaluator = self.build_evaluator(package_name, allow_yanked)
        extra_packages = self._evaluate_links(
            self.extra_links if self.extra_links is not None else [],
            evaluator
        )
        all_packages = itertools.chain(packages, extra_packages)
        all_packages = list(all_packages)
        return sorted(all_packages, key=self._sort_key, reverse=True)

class PyPIProvider:
    def __init__(self, index_urls, find_links, extra_links=[]):
        self.finder = CustomFinder(
            index_urls=index_urls, find_links=find_links,
            extra_links=extra_links
        )

    # does the lookup, without caching
    async def find_distributions(self, r: Requirement) -> list[Distribution]:
        results = list(self.finder.find_matches(r))

        # if any scheme is file...
        local_only = False
        for r in results:
            url = r.link.url
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme == "file":
                local_only = True
                break

        # map of version -> best_link we found
        versions = {}
        def proc_result(r):
            version = Version(r.version)
            curr = versions.get(version, None)
            url = r.link.url
            parsed = urllib.parse.urlparse(url)
            if local_only and parsed.scheme != "file":
                return None
            hash = None
            if r.link.hashes:
                if "sha256" in r.link.hashes:
                    hash = r.link.hashes["sha256"]
            src = URLDistribution(url, hash)
            if hash or curr is None:
                versions[version] = src
        for r in results: proc_result(r)
        order = sorted(versions.keys(), reverse=True)
        versions = [versions[o] for o in order]
        return versions

@dataclass
class CachedProvider(DistributionProvider):
    res: Resources
    provider : DistributionProvider
    cache_path : Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "source-cache")

    async def find_distributions(self, r: Requirement) -> list[Distribution]:
        # if url source is specified in the requirement,
        # return only the URL
        if r.url is not None:
            return [URLDistribution(r.url, None)]
        cache_loc = self.cache_path / f"{r.name}.json"
        sources = []
        if cache_loc.exists():
            with open(cache_loc, "r") as f:
                j = json.load(f)
                sources = [Distribution.from_json(s) for s in j]
            sources = [s for s in sources if s.version in r.specifier or s.version is None]
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