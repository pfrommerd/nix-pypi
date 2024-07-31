from .core import ProjectProvider, URLDistribution, SystemInfo
from .parser import URLParser, PyProjectParser
from .resources import CachedResources
from .distributions import (PyPIProvider, CachedProvider) 
from .resolver import Resolver
from .export import NixExporter

from pathlib import Path
from packaging.requirements import Requirement

import json
import urllib.parse
import tomllib
import logging

logger = logging.getLogger(__name__)

async def run(system_infos, project_path, output_path, lock_path, relock=False):
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
    extra_links_info = tool_info.get("extra-links", [])
    extra_links = []
    for e in extra_links_info:
        parsed = urllib.parse.urlparse(e)
        if parsed.scheme == "file":
            p = Path(parsed.path)
            # add all the files in the directory
            # as extra links
            if p.is_dir() and not (p / "pyproject.toml").exists():
                for e in p.iterdir():
                    extra_links.append(f"file://{e.resolve()}")
                continue
        extra_links.append(e)

    index_urls = tool_info.get("index-urls", ["https://pypi.org/simple/"])
    find_links = tool_info.get("find-links", [])

    overrides = set(tool_info.get("nixpkgs-overrides", []))

    provider = PyPIProvider(
        index_urls=index_urls, find_links=find_links, extra_links=extra_links
    )
    provider = CachedProvider(res, provider)
    projects = ProjectProvider(res, provider)
    resolver = Resolver(py_version, projects)
    # resolve the dependencies, and their associated
    # build environments. Returns all the recipes needed
    # for the specified requirement, as well as a set of build_recipes
    env_recipes, build_recipes = await resolver.resolve_recipes([requirement])

    # All recipes
    recipes = {}
    recipes.update(env_recipes)
    recipes.update(build_recipes)
    logger.info(f"All recipe ids: {','.join(recipes.keys())}")

    logger.info("Dependencies:")
    for r in env_recipes.values():
        build_env = r.env
        build_env = ", ".join([f"{recipes[r].name}=={recipes[r].version}" for r in build_env])
        if build_env:
            logger.info(f" {r.name}=={r.version} (building with {build_env})")
        else:
            logger.info(f" {r.name}=={r.version}")

    logger.info("Build Dependencies:")
    for r in build_recipes.values():
        build_env = r.env
        build_env = ", ".join([f"{recipes[r].name}=={recipes[r].version}" for r in build_env])
        if build_env:
            logger.info(f" {r.name}=={r.version} (building with {build_env})")
        else:
            logger.info(f" {r.name}=={r.version}")
    
    if output_path is not None:
        exporter = NixExporter(overrides)
        expr = exporter.expression(output_path, env_recipes, build_recipes)
        with open(output_path, "w") as f:
            f.write(expr)

def main():
    import sys
    import os
    import setuptools
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
    parser.add_argument("--python", "-i", default="3.10")
    parser.add_argument("--platforms", "-P", 
        action="append", default=[]
    )
    parser.add_argument("--project", "-p", default=".")
    parser.add_argument("--relock", "-r", action="store_true", default=False)
    parser.add_argument("--lock", "-l", default="requirements.lock")
    parser.add_argument("--output", "-o", default="requirements.nix")
    args = parser.parse_args()

    py_version = [int(i) for i in args.python.split(".")]
    platforms = args.platforms if args.platforms else ["x86_64-linux", "aarch64-darwin"]
    PLATFORM_MAP = {
        "x86_64-linux" : "linux_x86",
        "aarch64-darwin" : "darwin_aarch64"
    }
    platforms = [PLATFORM_MAP[p] for p in platforms]
    system_infos = [SystemInfo(py_version, p) for p in platforms]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run(
        system_infos,
        Path(args.project).resolve(), 
        Path(args.output).resolve(),
        Path(args.lock).resolve(),
        relock=args.relock
    ))