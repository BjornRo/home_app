import msgspec

from core import types

from . import internal_models


class Token(msgspec.Struct, array_like=True):
    iat: int
    exp: int
    sub: str


class NewToken(msgspec.Struct):
    access_token: str
    expires_in: int
    token_type = "Bearer"


type InternalAuthConnection = types.MyConnection[internal_models.InternalAppUser, Token]
type InternalAuthRequest = types.MyRequest[internal_models.InternalAppUser, Token]
