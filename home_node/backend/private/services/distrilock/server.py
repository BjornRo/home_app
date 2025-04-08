from __future__ import annotations

import asyncio
import os
import sys
import tomllib
from collections.abc import Callable
from multiprocessing import Process
from pathlib import Path
from typing import Literal, TypedDict

import serverlib.stores as stores
import uvloop  # type:ignore
from serverlib.utils import StoreBase, UnixTCPHandler
from shared import DEFAULT_UNIX_SOCK_ADDRESS

asyncio.set_event_loop(uvloop.new_event_loop())


def get_strat(strat: Literal["lock", "cache", "counter"] | str):
    match strat:
        case "lock":
            return lambda: stores.LockStore()
        case "cache":
            return lambda: stores.LockCache()
        case "counter":
            return lambda: stores.Counter()
        case x:
            raise ValueError("Unknown store given: " + str(x))


def pool_func(num_stores: int, addr_path: str, strat: str):
    asyncio.run(ProtocolUNIX(num_stores, addr_path, get_strat(strat)).run())


async def main():
    class ConfigItem(TypedDict):
        name: str
        num_stores: int
        strat: str

    class Config(TypedDict):
        servers: list[ConfigItem]

    with open("config.toml", "rb") as f:
        config: Config = tomllib.load(f)  # type:ignore

    path_prefix = sys.argv[1].lower()
    servers = [(x["num_stores"], f"/{path_prefix}/{x['name']}", x["strat"]) for x in config["servers"]]
    main_srv, *rest_srv = servers
    if rest_srv:
        child_procs = [Process(target=pool_func, args=x) for x in rest_srv]
        for i in child_procs:
            i.start()

    await ProtocolUNIX(*main_srv[:2], get_strat(main_srv[2])).run()


class ProtocolUNIX(UnixTCPHandler):
    def __init__(self, num_stores: int, filepath: str, store_type: Callable[[], StoreBase]):
        """path/to/me or just_me"""
        super().__init__(num_stores=num_stores, store_type=store_type)
        if not filepath:
            filepath = DEFAULT_UNIX_SOCK_ADDRESS
        elif filepath[0] == ".":
            raise ValueError("Invalid path")
        self.filepath = Path(filepath)

    async def run(self):
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
        else:
            os.makedirs(self.filepath.parent, exist_ok=True)
        try:
            server = await asyncio.start_unix_server(self.handler, path=self.filepath)  # type:ignore
            async with server:
                for i in self.store:
                    await i.init()
                await server.serve_forever()
        except:
            pass
        try:
            os.remove(self.filepath)
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
