from __future__ import annotations

__import__("sys").path.append("/")

import asyncio
import time

import db.distlock as dl
import msgspec
from db.internal.models import InternalRolesEnum
from litestar import WebSocket
from litestar.exceptions import ClientException, NotAuthorizedException
from litestar.handlers.websocket_handlers import WebsocketListener

from appdata.distrilock_client import ClientUnix, RequestMethods

from ._utils import get_jwt_auth_result


class WSArgs(msgspec.Struct):
    data: bytes | None | msgspec.UnsetType = msgspec.UNSET
    key: str | msgspec.UnsetType = msgspec.UNSET
    expiry: int | None | msgspec.UnsetType = msgspec.UNSET


class WSRequest(msgspec.Struct):
    method: RequestMethods
    args: WSArgs = msgspec.field(default_factory=WSArgs)


class InternalCacheController(WebsocketListener):
    decode = msgspec.msgpack.Decoder(WSRequest).decode
    encode = msgspec.msgpack.Encoder().encode
    path = "/cache/{store_name:str}"
    receive_mode = "binary"
    send_mode = "binary"
    description = "Client should reconnect when their token expires with a fresh token. Ease of implementation mostly"
    required_roles = (InternalRolesEnum.API, InternalRolesEnum.CACHE)

    @staticmethod
    async def terminate_ws_timer(socket: WebSocket, expiry: int):
        await asyncio.sleep(expiry - time.time())
        await socket.close()

    def cancel_task(self):
        try:
            self.expiry_task.cancel()
        except:
            pass

    async def on_accept(self, store_name: str, socket: WebSocket) -> None:
        if result := await get_jwt_auth_result(socket.headers):
            (_, roles), claims = result
            if roles.has_all_roles(self.required_roles) or roles.has_role(InternalRolesEnum.ROOT):
                try:
                    self.store: ClientUnix = getattr(dl, store_name)
                    self.expiry_task = asyncio.create_task(self.terminate_ws_timer(socket, claims["iat"]))
                except:
                    self.cancel_task()
                    raise ClientException("Invalid store")
        raise NotAuthorizedException

    async def on_disconnect(self, socket: WebSocket) -> None:
        self.cancel_task()

    async def on_receive(self, data: bytes) -> bytes:
        request_id = data[:8]
        request = self.decode(data[8:])

        match await getattr(self.store, request.method.name.lower())(
            **msgspec.to_builtins(request.args, builtin_types=(bytes,))
        ):
            case tuple() as t:
                request_id += (b"\x01" if t[0] else b"\x00") + t[1]
            case int(x):
                request_id += str(x).encode()
            case x:
                request_id += self.encode(x)
        return request_id
