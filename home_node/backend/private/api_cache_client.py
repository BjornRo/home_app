from __future__ import annotations

import asyncio
import secrets
import ssl
from dataclasses import dataclass, field
from enum import IntEnum
from typing import cast

import msgspec
from websockets.client import connect as wsconnect
from websockets.exceptions import ConnectionClosedOK

type ReturnResult = tuple[bool, bytes]


class RequestMethods(IntEnum):
    SIZE = 0
    KEYS = 1
    GET = 2
    SET = 3
    DELETE = 4
    UPDATE = 5


class WSArgs(msgspec.Struct):
    data: bytes | None | msgspec.UnsetType = msgspec.UNSET
    key: str | msgspec.UnsetType = msgspec.UNSET
    expiry: int | None | msgspec.UnsetType = msgspec.UNSET


class WSRequest(msgspec.Struct):
    method: RequestMethods
    args: WSArgs = msgspec.field(default_factory=WSArgs)


@dataclass
class CallbackItem:
    data: bytes
    channel: asyncio.Queue[bytes] = field(default_factory=lambda: asyncio.Queue(1))


class ClientWebSockets:
    __slots__ = ("callback_queue", "ws", "background_task", "uri", "certfile")
    encode = msgspec.msgpack.Encoder().encode
    keys_decoder = msgspec.msgpack.Decoder(list[str]).decode

    def __init__(self, uri: str, certfile: str | None = None):
        self.uri = uri
        self.certfile = certfile
        self.callback_queue: asyncio.Queue[CallbackItem] = asyncio.Queue()

    async def init(self):
        ssl_context = None
        if self.certfile:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_verify_locations(self.certfile)
        self.ws = await wsconnect(uri=self.uri, ssl=ssl_context)
        self.background_task = asyncio.create_task(self.connection_multiplexer())

    async def close(self):
        self.background_task.cancel()
        await self.ws.close()

    async def connection_multiplexer(self):
        waiting_callback: dict[bytes, asyncio.Queue[bytes]] = {}

        async def reader():
            try:
                while True:
                    resp: bytes = cast(bytes, await self.ws.recv())
                    request_id = resp[:8]

                    await waiting_callback[request_id].put(resp[8:])
                    del waiting_callback[request_id]  # Strong-ref @ _call(..) -> ok to delete.
            except ConnectionClosedOK:
                pass

        reader_task = asyncio.create_task(reader())
        while True:  # writer()
            item = await self.callback_queue.get()
            request_id = secrets.token_bytes(8)
            await self.ws.send(request_id + item.data)
            waiting_callback[request_id] = item.channel

    async def _call(self, request: WSRequest) -> bytes:
        cb = CallbackItem(data=self.encode(request))
        await self.callback_queue.put(cb)
        return await cb.channel.get()

    async def _res_call(self, request: WSRequest) -> ReturnResult:
        data = await self._call(request)
        print(data)
        return bool(data[0]), data[1:]

    async def size(self) -> int:
        data = await self._call(request=WSRequest(method=RequestMethods.SIZE))
        return int(data)

    async def keys(self, key: str = "0..10") -> list[str]:  # 4.. , ..3=0..3
        """start..end"""
        data = await self._call(request=WSRequest(method=RequestMethods.KEYS, args=WSArgs(key=key)))
        return self.keys_decoder(data)

    async def get(self, key: str):
        return await self._res_call(request=WSRequest(method=RequestMethods.GET, args=WSArgs(key=key)))

    async def set(self, key: str, expiry: int | None, data: bytes | None):
        req = WSRequest(method=RequestMethods.SET, args=WSArgs(key=key, expiry=expiry, data=data))
        return await self._res_call(request=req)

    async def update(self, key: str, expiry: int, data: bytes | None):
        """data:None does not update value, expiry"""
        req = WSRequest(method=RequestMethods.UPDATE, args=WSArgs(key=key, expiry=expiry, data=data))
        return await self._res_call(request=req)

    async def delete(self, key: str):
        return await self._res_call(request=WSRequest(method=RequestMethods.DELETE, args=WSArgs(key=key)))


async def main():
    ws = ClientWebSockets("wss://mqtt.lan:8000/internal/cache/misc_sensordata", "root.crt")
    await ws.init()
    import time

    start = time.time()
    print(await ws.get(key="kitchen"))
    print(await ws.size())
    print(await ws.keys())
    print(time.time() - start)
    await ws.close()
    pass


if __name__ == "__main__":
    asyncio.run(main())
