__import__("sys").path.append("/")
import time
from asyncio import gather
from datetime import datetime, timedelta
from functools import partial
from os import environ
from typing import Any, Callable, NamedTuple, TypedDict, cast

import jwt
import uvicorn
from litestar import Litestar, Request, WebSocket
from litestar.connection import ASGIConnection
from litestar.controller import Controller
from litestar.datastructures import Headers
from litestar.exceptions import (
    ClientException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.handlers import WebsocketListener
from litestar.handlers.base import BaseRouteHandler
from litestar.handlers.websocket_handlers import websocket_listener
from litestar.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.middleware.base import DefineMiddleware


class _JWTAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        res = connection.headers.get("Authorization")
        print(res)
        return AuthenticationResult(user=res, auth=res)


jwt_middleware = DefineMiddleware(_JWTAuthenticationMiddleware, exclude="schema")

# from appdata.distrilock_client import Request


# class InternalCacheController(WebsocketListener):
#     path = "/cache/{store_name:str}"
#     receive_mode = "binary"
#     send_mode = "binary"

#     async def on_accept(self, store_name: str, socket: WebSocket) -> None:
#         self.socket = socket
#         self.store = store_name

#     async def on_disconnect(self, socket: WebSocket) -> None:
#         pass

#     async def on_receive(self, data: bytes, socket: WebSocket) -> bytes:
#         raise ClientException
#         await self.socket.close(reason="lol")
#         print(socket.headers)
#         print(socket.headers)
#         return data + self.store.encode()


class InternalCacheController(Controller):
    path = "/cache"
    # receive_mode = "binary"
    # send_mode = "binary"

    @websocket_listener("/{store_name:str}", receive_mode="binary", send_mode="binary")
    async def handler(self, data: bytes, store_name: str, socket: WebSocket) -> bytes:
        print(data)
        await socket.close()
        # print("printer", await socket.receive())
        print(store_name)
        print(socket)
        return data


app = Litestar(route_handlers=[InternalCacheController], debug=False)

if __name__ == "__main__":
    uvicorn.run(app=app)
