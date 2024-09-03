import urllib.parse
import requests
import asyncio
import os.path
import concurrent.futures
import json
import hashlib
import contextlib

from io import BytesIO
from typing import IO
from pathlib import Path

class Resources:
    def __init__(self, max_workers=16):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    # will fetch a url,
    # and return an IO object from the url
    @contextlib.asynccontextmanager
    async def fetch(self, url: str) -> IO | Path | None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme == "file":
            path = Path(parsed.path)
            if path.is_dir():
                yield path
            else:
                with open(parsed.path) as f:
                    yield f
        elif parsed.scheme == "http" or parsed.scheme == "https":
            io_loop = asyncio.get_event_loop()
            def do_fetch():
                r = requests.get(url, allow_redirects=True)
                return r.content
            c = await io_loop.run_in_executor(self.executor, do_fetch)
            yield BytesIO(c)
        else:
            raise ValueError(f"Unrecognized scheme: {parsed.scheme} in {url}")

class CachedResources(Resources):
    def __init__(self, cache_dir, max_workers=16):
        super().__init__(max_workers=max_workers)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    @contextlib.asynccontextmanager
    async def fetch(self, url: str) -> IO | Path | None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme == "file":
            async with super().fetch(url) as r:
                yield r
        else:
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
            filename = os.path.basename(parsed.path)
            cache_key = f"{filename}-{digest}"
            cache_location = self.cache_dir / cache_key
            if not cache_location.exists():
                async with super().fetch(url) as f:
                    # write f to the cache
                    with open(cache_location, "wb") as o:
                        o.write(f.read())
            with open(cache_location, "rb") as f:
                yield f
