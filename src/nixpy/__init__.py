from .core import Project, ProjectsManager, PyPISourceProvider, LocalSource, RemoteSource, CustomSource
from .resolver import Resolver
from pathlib import Path
from packaging.requirements import Requirement

import urllib.parse

def main():
    import logging
    import argparse
    import asyncio
    from rich.logging import RichHandler
    FORMAT = "%(message)s"
    logging.basicConfig(
        level=logging.ERROR, format=FORMAT, 
        datefmt="[%X]", handlers=[RichHandler()]
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(prog="nixpy")
    parser.add_argument("requirements", nargs="*")
    parser.add_argument("--index", "-I", action="append", default=[])
    parser.add_argument("--find", "-f", action="append", default=[])
    parser.add_argument("--custom", "-c", action="append", default=[])
    args = parser.parse_args()

    indices, find_links, custom = [], [], []
    for p in args.index:
        url = urllib.parse.urlparse(p)
        if not url.scheme: indices.append("file://" + str(Path(p).resolve()))
        else: indices.append(p)
    for p in args.find:
        url = urllib.parse.urlparse(p)
        if not url.scheme: find_links.append("file://" + str(Path(p).resolve()))
        else: find_links.append(p)
    for p in args.custom:
        n, v = p.split("==")
        custom.append(CustomSource(n, v))

    async def req_from_path(r):
        project = await Project.load_from_directory(LocalSource(r), r)
        return Requirement(f"{project.name} @ file://{r.resolve()}")

    # can also handle local paths
    async def run():
        requirements = [await req_from_path(Path(r)) if Path(r).exists() else Requirement(r) for r in args.requirements]
        provider = PyPISourceProvider(index_urls=["https://pypi.org/simple/"] + indices, find_links=find_links)
        projects = ProjectsManager(src_provider=provider)
        # populate all of the custom-built projects
        for s in custom: projects.add_project(await s.load(projects))
        resolver = Resolver(projects)
        main_environment = await resolver.resolve(requirements)
        resolution = ", ".join([f"{r.name}=={r.version}" for r in main_environment])
        logger.debug(f"resolved: {resolution}")
        # each build environment can be resolved separately...
        # do this in parallel
        async def resolve_build_env(candidate):
            # Only resolve build environments for non-wheel sources
            if candidate.project.source.is_wheel:
                return None
            logger.info(f"resolving build environment for {b.name}")
            env = await resolver.resolve(candidate.build_dependencies)
            resolution = ", ".join([f"{r.name}=={r.version}" for r in env])
            logger.debug(f"resolved build env for {b.name}: {resolution}")
            return env
        logger.info("resolving build environments...")
        build_envs = []
        for b in main_environment:
            build_envs.append(await resolve_build_env(b))
        build_envs = {f"{r.name}-{r.version}": e for (r, e) in zip(main_environment, build_envs) if e is not None}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())