from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Iterable

import aiosqlite

# No pool for this. Expecting low usage. If higher usage, swap for API database


class INTERNALSQLite:
    __slots__ = ("_dbfile",)

    def __init__(self, dbfile: str) -> None:
        self._dbfile = dbfile

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        async with aiosqlite.connect(self._dbfile) as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("PRAGMA journal_mode = WAL")
            await conn.execute("PRAGMA synchronous = NORMAL")
            await conn.execute("PRAGMA cache_size = 100")
            await conn.execute("PRAGMA temp_store = MEMORY")
            conn.row_factory = aiosqlite.Row
            yield conn

    async def fetch_all(self, query: str, params: Iterable[Any] | None = None) -> Iterable[Any]:
        async with self.connect() as conn:
            return await conn.execute_fetchall(query, params)

    async def fetch_one(self, query: str, params: Iterable[Any] | None = None) -> Any | None:
        async with self.connect() as conn:
            cur = await conn.execute(query, params)
            return await cur.fetchone()

    async def execute_void(self, query: str, params: Iterable[Any]) -> None:
        """Return nothing. Should be for INSERT, UPDATE, DELETE"""
        async with self.connect() as conn:
            await conn.execute(query, params)
            await conn.commit()
