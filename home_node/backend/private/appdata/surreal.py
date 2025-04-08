from __future__ import annotations

import asyncio
import time
from datetime import timedelta
from types import TracebackType
from typing import Any, Literal, NamedTuple, Optional, Type, TypedDict
from uuid import uuid4

import msgspec
from websockets.legacy import client as ws

uuid_func = uuid4


class Request(msgspec.Struct, frozen=True):
    method: str
    params: tuple
    id: str = msgspec.field(default_factory=lambda: str(uuid_func()))


class APIResult(NamedTuple):
    ok: bool
    data: Any


class QueryResult(TypedDict):
    result: Any
    status: Literal["OK", "ERR"]
    time: str


class ResponseSuccess(TypedDict):
    result: list[QueryResult]
    id: str | None


class ResponseError(TypedDict):
    code: int
    message: str


class Surreal:
    __slots__ = ("ws", "is_closing", "timeout_task", "last_used")
    _decode = msgspec.json.Decoder().decode
    _encode = msgspec.json.Encoder().encode

    def __init__(self) -> None:
        self.last_used = time.time()
        self.timeout_task = None
        self.is_closing = False

    async def __aenter__(self) -> Surreal:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_value: Optional[Type[BaseException]] = None,
        traceback: Optional[Type[TracebackType]] = None,
    ) -> None:
        await self.close()

    async def _timeout_watchdog(self, timeout: float, leeway: int = 10):
        await asyncio.sleep(timeout + leeway)
        while not self.closed():
            _time = time.time()
            last_used_delta = self.last_used + timeout
            if last_used_delta <= _time:
                self.is_closing = True
                await self.close()
                return
            await asyncio.sleep(last_used_delta - _time + leeway)

    async def connect(self, url: str, idle_timeout: None | timedelta = None):
        self.ws = await ws.connect(url)
        self.last_used = time.time()
        if idle_timeout:
            self.timeout_task = asyncio.create_task(self._timeout_watchdog(idle_timeout.total_seconds()))
        return self

    async def close(self):
        await self.ws.close()

    def closed(self):  # Conn Queue asks if it is closed, while we have control, update to prevent closing
        self.last_used = time.time()
        return self.is_closing or self.ws.closed

    async def _send_receive(self, method: str, params: tuple = ()) -> APIResult:
        await self.ws.send(self._encode(Request(method=method, params=params)).decode())
        try:
            response: ResponseSuccess = self._decode(await self.ws.recv())  # | ResponseError
            result = response["result"].pop()
            return APIResult(ok=result["status"] != "ERR", data=result["result"])
        except:
            raise Exception(response["error"]["message"])  # type:ignore

    async def use(self, namespace: str, database: str):
        await self.ws.send(self._encode(Request(method="use", params=(namespace, database))).decode())
        await self.ws.recv()
        return self

    async def query(self, sql: str, vars: Optional[dict[str, Any]] = None) -> APIResult:
        return await self._send_receive(method="query", params=(sql,) if vars is None else (sql, vars))
