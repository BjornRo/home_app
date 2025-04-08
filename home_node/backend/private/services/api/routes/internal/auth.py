from asyncio import gather

import db.distlock as dl
import db.internal.queries as internal_queries
from constants import HEADER_IP_KEY, MAX_LOGIN_ATTEMPS_PER_IP, MAX_LOGIN_TIMEOUT
from litestar import get, post
from litestar.controller import Controller
from litestar.datastructures.headers import Headers
from litestar.exceptions import NotAuthorizedException, TooManyRequestsException
from mytypes import NamePWD
from routes.auth import NewToken
from utils import fire_forget_coro

from ._utils import (
    InternalAuthRequest,
    generate_token,
    jwt_internal_middleware,
    token_expiry,
    verify_password,
)

LOGIN_TIMEOUT_SEC = 900


class InternalAuthController(Controller):
    path = "/auth"
    tags = ["internal_auth"]

    @post(
        path="/login",
        status_code=200,
        raises=[NotAuthorizedException, TooManyRequestsException],
    )
    async def login(self, data: NamePWD, headers: Headers) -> NewToken:
        if ip := headers.get(HEADER_IP_KEY):
            _, attempts = await dl.count_login_attempts.set(key=ip, expiry=MAX_LOGIN_TIMEOUT, data=None)
            if int.from_bytes(attempts) > MAX_LOGIN_ATTEMPS_PER_IP:
                raise TooManyRequestsException
            user_id, _ = await verify_password(**data)
            fire_forget_coro(dl.count_login_attempts.delete(key=ip))
        else:
            user_id, _ = await verify_password(**data)

        # To stop too many logins for a specific id, it wont clash with ip addresses due the shape of str
        _, attempts = await dl.count_login_attempts.set(key=user_id, expiry=LOGIN_TIMEOUT_SEC, data=None)
        if int.from_bytes(attempts) <= 1:
            await internal_queries.upsert_internal_token_valid_from_date(user_id)
            return NewToken(access_token=generate_token(user_id=user_id), expires_in=token_expiry)
        raise TooManyRequestsException

    @get(
        path="/logout",
        security=[{"BearerToken": []}],
        description="Invalidates all tokens from this date",
        middleware=[jwt_internal_middleware],
        status_code=204,
    )
    async def logout(self, request: InternalAuthRequest) -> None:
        user_id, _ = request.user
        await gather(
            internal_queries.delete_internal_all_cache(user_id),
            internal_queries.upsert_internal_token_valid_from_date(user_id),
        )
        return None

    # @get(
    #     path="/token",
    #     security=[{"BearerToken": []}],
    #     raises=[NotAuthorizedException],
    #     description="Get new token from token using cookies",
    # )
    # async def token(self, headers: Headers) -> NewToken:
    #     try:
    #         if token_str := get_token_str(headers):
    #             user_id = verify_token(token_str)["sub"]
    #             if await internal_queries.cache_user_exists(user_id):
    #                 return NewToken(access_token=generate_token(user_id), expires_in=token_expiry)
    #     except:
    #         pass
    #     raise NotAuthorizedException
