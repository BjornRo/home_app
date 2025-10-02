from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Any, Callable, NamedTuple, TypedDict

from appdata import shared  # type: ignore
from litestar.connection import ASGIConnection, Request
from litestar.datastructures import State
from litestar.exceptions import HTTPException
from litestar.handlers.base import BaseRouteHandler
from litestar.status_codes import HTTP_409_CONFLICT
from msgspec import Struct, convert, json, to_builtins

from core import exceptions, models

type DateT = shared.DateTimeUTC | timedelta | None
type Unixtime = int
type UserID = str
type Password = str
type MyRequest[T, X] = Request[T, X, State]
type MyConnection[T, X] = ASGIConnection[BaseRouteHandler, T, X, State]
type DateTimeStr = str

type AuthRequest = MyRequest[models.AppUser, JWTToken]
type AuthConnection = MyConnection[models.AppUser, JWTToken]


# region: Key management (JWT)
class Keys(Struct, gc=False):
    private: str
    public: str


class KeyData(Struct, gc=False):
    created: shared.DateTimeUTC
    keys: Keys
    public_key_sign: str


class JWTToken(Struct):
    exp: int
    iat: int
    sub: str
    iss: str
    aud: list[str]

    def to_dict(self) -> dict[str, Any]:
        return to_builtins(self)

    @staticmethod
    def from_dict(data: dict[str, Any]):
        return convert(data, type=JWTToken)

    @staticmethod
    def loads(data: bytes) -> JWTToken:
        return __decoder(data)


class JWTEncDec(NamedTuple):
    encode: Callable[[dict[str, Any]], str]
    decode: Callable[[str], JWTToken]


# endregion


class Credentials(TypedDict):
    login: str
    pwd: str


class AlreadyExists(HTTPException):
    status_code = HTTP_409_CONFLICT
    detail = "Value already exists"


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class RWX(Struct):
    read: bool
    write: bool
    execute: bool

    @staticmethod
    def from_int(rwx: int) -> RWX:
        if 0 <= rwx <= 7:
            return RWX(read=bool(rwx & 0b100), write=bool(rwx & 0b10), execute=bool(rwx & 1))
        raise exceptions.UserInputError("RWX is invalid, number between 0-7")

    def to_int(self):
        return self.read << 2 | self.write << 1 | self.execute


__decoder = json.Decoder(JWTToken).decode
