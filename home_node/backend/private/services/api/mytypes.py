from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, TypedDict

from litestar.connection import ASGIConnection, Request
from litestar.datastructures import State
from litestar.exceptions import ClientException
from litestar.handlers.base import BaseRouteHandler
from litestar.status_codes import HTTP_409_CONFLICT
from msgspec import Struct

type DateT = DateTimeUTC | timedelta | None
type DateTimeUTC = Annotated[datetime, ...]
type UserID = str
type UserID_Result[T] = tuple[UserID, T]
type Password = str
type MyRequest[T, X] = Request[T, X, State]
type MyConnection[T, X] = ASGIConnection[BaseRouteHandler, T, X, State]


# region: Key management (JWT)
class Keys(Struct, gc=False):
    private: str
    public: str


class KeyData(Struct, gc=False):
    created: DateTimeUTC
    keys: Keys
    public_key_sign: str


# endregion


class NamePWD(TypedDict):
    name: str
    pwd: str


class ItemAlreadyExistException(ClientException):
    status_code = HTTP_409_CONFLICT


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
