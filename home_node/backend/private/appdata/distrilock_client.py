from __future__ import annotations

import asyncio
import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from struct import Struct
from typing import cast, override

import msgspec

type ReturnResult = tuple[bool, bytes]

DEFAULT_UNIX_SOCK_ADDRESS = "/dev/shm/dlserver.sock"

response_protocol = Struct(">?H")  # Q: int_id, ?: Ok/Err, H: Header_len for data following


class RequestMethods(IntEnum):
    SIZE = 0
    KEYS = 1
    GET = 2
    SET = 3
    DELETE = 4
    UPDATE = 5


class Request(msgspec.Struct):
    index: int
    method: RequestMethods
    key: str
    expiry: int | None
    data_len: int | None

    def __post_init__(self):
        self.key = self.key.lower()


class ClientBase(ABC):
    __slots__ = "store_id"
    encoder = msgspec.msgpack.Encoder().encode
    keys_decoder = msgspec.msgpack.Decoder(list[str]).decode

    def __init__(self, store_id: int):
        self.store_id = store_id

    async def init(self):
        pass

    async def close(self):
        pass

    @abstractmethod
    async def _call(self, request: Request, data: bytes | None = None) -> ReturnResult: ...

    async def size(self) -> int:
        req = Request(index=self.store_id, method=RequestMethods.SIZE, key="", expiry=None, data_len=None)
        ok, data = await self._call(request=req)
        if ok:
            return int(data)
        return -1

    async def keys(self, key: str = "0..10") -> list[str]:
        """start..end | One value can be omitted"""
        req = Request(
            index=self.store_id,
            method=RequestMethods.KEYS,
            key=key,
            expiry=None,
            data_len=None,
        )
        ok, data = await self._call(request=req)
        if ok:
            return self.keys_decoder(data)
        return []

    async def get(self, key: str):
        req = Request(index=self.store_id, method=RequestMethods.GET, key=key, expiry=None, data_len=None)
        return await self._call(request=req)

    async def set(self, key: str, expiry: int | None, data: bytes | None):
        req = Request(
            index=self.store_id,
            method=RequestMethods.SET,
            key=key,
            expiry=expiry,
            data_len=len(data) if data else None,
        )
        return await self._call(request=req, data=data)

    async def update(self, key: str, expiry: int, data: bytes | None):
        """data:None does not update value, expiry"""
        hl = None if data is None else len(data)
        req = Request(index=self.store_id, method=RequestMethods.UPDATE, key=key, expiry=expiry, data_len=hl)
        return await self._call(request=req, data=data)

    async def delete(self, key: str):
        req = Request(index=self.store_id, method=RequestMethods.DELETE, key=key, expiry=None, data_len=None)
        return await self._call(request=req)


@dataclass
class CallbackItem:
    headers: bytes
    data: bytes | None
    channel: asyncio.Queue[ReturnResult] = field(default_factory=lambda: asyncio.Queue(1))


class ClientUnixTCPBase(ClientBase):
    __slots__ = ("callback_queue", "reader", "writer", "background_task")

    def __init__(self, store_id: int):
        super().__init__(store_id)
        self.callback_queue: asyncio.Queue[CallbackItem] = asyncio.Queue()

    @override
    async def init(self):
        self.reader, self.writer = await self._connect()
        self.background_task = asyncio.create_task(self.connection_multiplexer())

    @override
    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    async def connection_multiplexer(self):
        waiting_callback: dict[bytes, asyncio.Queue[ReturnResult]] = {}

        async def reader():
            while True:
                resp = await self.reader.readexactly(11)
                request_id = resp[:8]
                ok, header_len = cast(tuple[bool, int], response_protocol.unpack(resp[8:]))
                data = await self.reader.readexactly(header_len) if header_len else b""
                await waiting_callback[request_id].put((ok, data))
                del waiting_callback[request_id]  # Strong-ref @ _call(..) -> ok to delete.

        reader_task = asyncio.create_task(reader())
        while True:  # writer()
            item = await self.callback_queue.get()
            request_id = secrets.token_bytes(8)
            self.writer.write(request_id + len(item.headers).to_bytes())
            self.writer.write(item.headers)
            if item.data:
                self.writer.write(item.data)
            waiting_callback[request_id] = item.channel
            await self.writer.drain()

    @abstractmethod
    async def _connect(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]: ...

    async def _call(self, request: Request, data: bytes | None = None) -> ReturnResult:
        cb = CallbackItem(headers=self.encoder(request), data=data)
        await self.callback_queue.put(cb)
        return await cb.channel.get()


class ClientUnix(ClientUnixTCPBase):
    __slots__ = "filepath"

    def __init__(self, store_id: int, path: str):
        super().__init__(store_id)
        self.filepath = Path(DEFAULT_UNIX_SOCK_ADDRESS) if path == "" else Path(path)

        if not os.path.exists(self.filepath):
            raise RuntimeError("DL server is not running")

    async def _connect(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        return await asyncio.open_unix_connection(self.filepath)  # type:ignore
