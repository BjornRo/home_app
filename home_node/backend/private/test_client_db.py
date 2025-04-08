import asyncio
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable, Generator, Literal, TypedDict, cast

from surrealdb import Surreal


class QueryResult(TypedDict):
    result: Any  # str IF err
    status: Literal["OK", "ERR"]
    time: str


type DBResult = list[QueryResult]


class SurrealSimple:
    def __init__(self, namespace="app", database="api"):
        self.ns, self.db = namespace, database

    async def query(self, query: str, query_args: dict[str, Any] | None = None) -> DBResult:
        async with Surreal("ws://127.0.0.1:8000/rpc") as db:
            await db.use(namespace=self.ns, database=self.db)
            return cast(DBResult, await db.query(query, query_args))


def encrypt():
    raise Exception(123)
    time.sleep(2)
    return b"sss"


async def pool_runner(func: Callable, pool=ProcessPoolExecutor(2)):
    return await asyncio.get_event_loop().run_in_executor(pool, func)


async def main():
    start = time.time()
    # await pool_runner()
    res = await SurrealSimple().query('CREATE user_data:123 SET name = "pizw"')
    # print(12)
    # res = await asyncio.gather(
    #     pool_runner(encrypt),
    #     pool_runner(encrypt),
    #     pool_runner(encrypt),
    #     pool_runner(encrypt),
    #     pool_runner(encrypt),
    #     pool_runner(encrypt),
    #     pool_runner(encrypt),
    #     pool_runner(encrypt),
    # )
    print(time.time() - start)
    print(res)


if __name__ == "__main__":
    asyncio.run(main())
