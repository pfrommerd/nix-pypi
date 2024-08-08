from .core import ProjectProvider, URLDistribution, SystemInfo
from .parser import URLParser, PyProjectParser
from .resources import CachedResources
from .distributions import (
    PyPIProvider, CustomProvider, CombinedProvider,
    CachedProvider
) 
from .resolver import Resolver
from .export import NixExporter

from pathlib import Path
from packaging.requirements import Requirement

import json
import urllib.parse
import logging
import importlib

logger = logging.getLogger(__name__)

# Maps nix platform names to the python platform names
PYTHON_PLATFORM_MAP = {
    "x86_64-linux" : "linux_x86",
    "aarch64-darwin" : "darwin_aarch64"
}

async def run(project_path, output_path, custom_paths):
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
    py_version = tool_info.get("python-version", None)
    if py_version is None:
        logger.error("Must specify python-version in [tool.nixpy] section.")
        return
    py_version = tuple(int(i) for i in py_version.split("."))

    platforms = tool_info.get("platforms", None)
    if platforms is None:
        logger.error("Must specify target platforms in [tool.nixpy] section.")
        return
    system_infos = [
        SystemInfo(py_version, n) for n in platforms
    ]
    index_urls = tool_info.get("index-urls", ["https://pypi.org/simple/"])
    find_links = tool_info.get("find-links", [])

    pypi_provider = CachedProvider(res, 
        PyPIProvider(
            index_urls=index_urls, find_links=find_links
        )
    )
    providers = [CustomProvider(p) for p in custom_paths]
    provider = CombinedProvider(providers + [pypi_provider])
    projects = ProjectProvider(res, provider)
    resolver = Resolver(projects)
    # resolve the dependencies, and their associated
    # build environments. Returns all the recipes needed
    # for the specified requirement, as well as a set of build_recipes
    environments = []
    for system in system_infos:
        environments.append(await resolver.resolve_environment(
            system, [requirement]
        ))
    if output_path is not None:
        exporter = NixExporter(custom_paths, output_path.parent)
        expr = exporter.expression(environments)
        with open(output_path, "w") as f:
            f.write(expr)

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
    parser.add_argument("--relock", "-r", action="store_true", default=False)
    parser.add_argument("--output", "-o", default="requirements.nix")
    parser.add_argument("--custom", "-c", action="append", default=[])
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run(
        Path(args.project).resolve(), 
        Path(args.output).resolve(),
        [Path(p).resolve() for p in args.custom]
    ))