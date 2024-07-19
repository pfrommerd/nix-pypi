from .core import ProjectProvider, URLDistribution
from .parser import URLParser, PyProjectParser
from .resources import CachedResources
from .distributions import (PyPIProvider, CachedProvider) 
from .resolver import Resolver

from pathlib import Path
from packaging.requirements import Requirement

import urllib.parse
import tomllib
import logging

logger = logging.getLogger(__name__)

async def run(project_path, output_path):
    res = CachedResources()
    # make the project requirement
    src = URLDistribution(f"file://{project_path}")
    project = await URLParser().parse(src, src.url, res)
    requirement = Requirement(f"{project.name} @ {src.url}")
    # parse the project file to extract any 
    # [tools.nixpy] links
    tool_info = await PyProjectParser().parse_tool_info(
        project_path / "pyproject.toml", tool_name="nixpy"
    )
    # get any extra source links for nixpy to use
    extra_links = tool_info.get("extra-links", [])
    index_urls = tool_info.get("index-urls", ["https://pypi.org/simple/"])
    find_links = tool_info.get("find-links", [])

    provider = PyPIProvider(
        index_urls=index_urls, find_links=find_links, extra_links=extra_links
    )
    provider = CachedProvider(res, provider)
    projects = ProjectProvider(res, provider)

    resolver = Resolver(projects)
    # resolve the dependencies, and their associated
    # build environments. Returns all the recipes needed
    # for the specified requirement, as well as a set of build_recipes
    recipes, build_recipes = await resolver.resolve_recipes([requirement])

    logger.info("Dependencies:")
    for r in recipes:
        build_env = r.dependencies + r.build_dependencies
        build_env = ", ".join([f"{r.name}=={r.version}" for r in build_env])
        if build_env:
            logger.info(f" {r.name}=={r.version} (building with {build_env})")
        else:
            logger.info(f" {r.name}=={r.version}")

    logger.info("Build Dependencies:")
    for r in build_recipes:
        build_env = r.dependencies + r.build_dependencies
        build_env = ", ".join([f"{r.name}=={r.version}" for r in build_env])
        if build_env:
            logger.info(f" {r.name}=={r.version} (building with {build_env})")
        else:
            logger.info(f" {r.name}=={r.version}")

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
    parser.add_argument("--project", "-p", default=".")
    parser.add_argument("--output", "-o", default="requirements.nix")
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run(Path(args.project).resolve(), Path(args.output).resolve()))