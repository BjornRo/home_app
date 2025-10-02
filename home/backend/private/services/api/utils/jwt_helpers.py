import base64
from functools import partial
from typing import Any

import jwt
from core import jwt_config, types
from utils import helpers, time_helpers


def unsafe_decode_token(token_str: str):
    return types.JWTToken.loads(
        base64.urlsafe_b64decode(token_str[token_str.find(".") + 1 : token_str.rfind(".")] + "==")
    )


async def gen_refresh_token(user_id: str):
    _time = time_helpers.unixtime()
    tok: Any = types.JWTToken(
        exp=_time + jwt_config.REFRESH_TIMEDELTA,
        iat=_time,
        sub=user_id,
        iss=jwt_config.ISS,
        aud=[jwt_config.ISS],
    )
    return await helpers.pool_runner(jwt_refresh.encode, tok.to_dict())


async def gen_access_token(user_id: str, aud: list[str] = list(jwt_config.AUD.values())):
    _time = time_helpers.unixtime()
    expiry = _time + jwt_config.ACCESS_TIMEDELTA
    tok = types.JWTToken(
        exp=expiry,
        iat=_time,
        sub=user_id,
        iss=jwt_config.ISS,
        aud=aud,
    )
    return await helpers.pool_runner(jwt_access.encode, tok.to_dict()), expiry


def __decode(token: str, is_access: bool, opts: dict[str, bool] | None = {"verify_aud": False}):
    if is_access:
        claims = types.JWTToken.from_dict(
            jwt.decode(
                jwt=token,
                key=jwt_config.ACCESS_KEYDATA.keys.public,
                algorithms=jwt_config.ALGORITHMS,
                options=opts,
            )
        )
        if jwt_config.AUD["api"] in claims.aud:
            return claims
    else:
        claims = types.JWTToken.from_dict(
            jwt.decode(
                jwt=token,
                key=jwt_config.REFRESH_KEYDATA.keys.public,
                algorithms=jwt_config.ALGORITHMS,
                options=opts,
            )
        )
        if jwt_config.ISS == claims.aud[0]:
            return claims
    raise jwt.InvalidAudienceError


jwt_refresh = types.JWTEncDec(
    encode=partial(jwt.encode, key=jwt_config.REFRESH_KEYDATA.keys.private, algorithm=jwt_config.ALGORITHMS[0]),
    decode=partial(__decode, is_access=False),
)
jwt_access = types.JWTEncDec(
    encode=partial(jwt.encode, key=jwt_config.ACCESS_KEYDATA.keys.private, algorithm=jwt_config.ALGORITHMS[0]),
    decode=partial(__decode, is_access=True),
)
