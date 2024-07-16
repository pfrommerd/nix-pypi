from .core import Project, ProjectsManager, PyPISourceProvider, LocalSource
from .resolver import Resolver
from pathlib import Path
from packaging.requirements import Requirement

def main():
    import logging
    import argparse
    import asyncio
    from rich.logging import RichHandler
    FORMAT = "%(message)s"
    logging.basicConfig(
        level=logging.INFO, format=FORMAT, 
        datefmt="[%X]", handlers=[RichHandler()]
    )

    parser = argparse.ArgumentParser(prog="nixpy")
    parser.add_argument("requirements", nargs="*")
    args = parser.parse_args()
    print(args.requirements)

    def req_from_path(r):
        project = Project.parse_from_directory(LocalSource(r), r)
        return Requirement(f"{project.name} @ {r}")
    # can also handle local paths
    requirements = [req_from_path(Path(r)) if Path(r).exists() else Requirement(r) for r in args.requirements]
    async def run():
        provider = PyPISourceProvider(["https://pypi.org/simple/"])
        projects = ProjectsManager(src_provider=provider)
        resolver = Resolver(projects)
        await resolver.resolve(requirements)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())