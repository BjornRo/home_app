from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Iterable

import aiosqlite
import aiosqlitepool

type DBConnection = aiosqlite.Connection


class SQLite:
    __slots__ = ("_pool",)

    def __init__(self, dbfile: str, pool_size=5) -> None:
        async def _connection_factory() -> DBConnection:
            conn = await aiosqlite.connect(dbfile)
            await conn.execute("PRAGMA journal_mode = WAL")
            await conn.execute("PRAGMA synchronous = NORMAL")
            await conn.execute("PRAGMA cache_size = 5000")
            await conn.execute("PRAGMA temp_store = MEMORY")
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("PRAGMA mmap_size = 268435456")
            conn.row_factory = aiosqlite.Row

            return conn

        self._pool = aiosqlitepool.SQLiteConnectionPool(
            connection_factory=_connection_factory,  # type: ignore
            pool_size=pool_size,
        )

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[DBConnection, None]:
        async with self._pool.connection() as conn:
            yield conn  # type: ignore

    async def close(self) -> None:
        await self._pool.close()

    async def fetch_all(self, query: str, params: Iterable[Any] | None = None) -> Iterable[Any]:
        conn: DBConnection
        async with self._pool.connection() as conn:  # type: ignore
            return await conn.execute_fetchall(query, params)

    async def fetch_one(self, query: str, params: Iterable[Any] | None = None) -> Any | None:
        conn: DBConnection
        async with self._pool.connection() as conn:  # type: ignore
            cur = await conn.execute(query, params)
            return await cur.fetchone()

    async def execute_void(self, query: str, params: Iterable[Any]) -> None:
        """Return nothing. Should be for INSERT, UPDATE, DELETE"""
        conn: DBConnection
        async with self._pool.connection() as conn:  # type: ignore
            await conn.execute(query, params)
            await conn.commit()
