import time
from dataclasses import dataclass
from typing import NotRequired, TypedDict

import db.distlock as dl
import db.queries as queries
from constants import DEFAULT_SECURITY_TAG as SECTAG
from constants import HEADER_IP_KEY, MAX_LOGIN_ATTEMPS_PER_IP, MAX_LOGIN_TIMEOUT
from db.distlock import api_request_cache
from db.models import TableAPI
from litestar import get, post
from litestar.controller import Controller
from litestar.datastructures.headers import Headers
from litestar.exceptions import (
    ClientException,
    NotAuthorizedException,
    TooManyRequestsException,
)
from litestar.params import Parameter
from modules.guards import root_api_jwt_guard, root_guard, root_or_local_jwt_guard
from modules.myjwt import AuthRequest, jwt_middleware
from mytypes import NamePWD, UserID
from typing_extensions import Annotated
from utils import fire_forget_coro

from ._utils import verify_password

LOGIN_TIMEOUT_SEC = 900

CACHE_DURATION = 30  # cache duration in seconds


async def get_service_names(cache_key="service_names", cache_duration=CACHE_DURATION) -> list[str]:
    ok, data = await api_request_cache.get(cache_key)
    if ok:
        return data.decode().split(",") if data else []

    dbdata: list[str] = (await queries.query("SELECT VALUE meta::id(id) FROM service")).data
    await api_request_cache.set(cache_key, cache_duration, ",".join(dbdata).encode())
    return dbdata


@dataclass
class RegisterService:
    credentials: NamePWD
    name: str
    url: str
    description: str

    def get_dict(self):
        return {
            "name": self.name.lower(),
            "url": self.url.lower(),
            "description": self.description,
        }


class Service(TypedDict):
    name: str
    url: str
    description: str
    created: str


class InternalServiceController(Controller):
    path = "/service"
    tags = ["internal_service"]

    @get(path="/", security=SECTAG, guard=[root_or_local_jwt_guard], status_code=200, cache=60)
    async def service_list(self) -> list[Service]:
        resp = await queries.query("SELECT *,meta::id(id) AS name FROM service")
        return resp.data

    @get(path="/names", security=SECTAG, guard=[root_or_local_jwt_guard], status_code=200)
    async def service_names(self) -> list[str]:
        return await get_service_names()

    @post(
        path="/register",
        status_code=200,
        raises=[NotAuthorizedException, TooManyRequestsException, ClientException],
    )
    async def register_service(self, data: RegisterService, headers: Headers) -> None:
        if ip := headers.get(HEADER_IP_KEY):
            _, attempts = await dl.count_login_attempts.set(key=ip, expiry=MAX_LOGIN_TIMEOUT, data=None)
            if int.from_bytes(attempts) > MAX_LOGIN_ATTEMPS_PER_IP:
                raise TooManyRequestsException
            user_id, _ = await verify_password(**data.credentials)
            fire_forget_coro(dl.count_login_attempts.delete(key=ip))
        else:
            user_id, _ = await verify_password(**data.credentials)

        # To stop too many logins for a specific id, it wont clash with ip addresses due the shape of str
        _, attempts = await dl.count_login_attempts.set(key=user_id, expiry=LOGIN_TIMEOUT_SEC, data=None)
        if int.from_bytes(attempts) > 1:
            raise TooManyRequestsException
        if "," in data.name:
            raise ClientException("Invalid name")
        await queries.query(
            "LET $obj=SELECT * FROM ONLY type::thing('service',$name);"
            "IF $obj=NONE {"
            f" CREATE ONLY type::thing('service',$name) SET name=$name,url=$url,description=$description"
            "} ELSE {"
            "  IF $obj.description!=$description {UPDATE ONLY $obj.id SET description=$description};"
            "  IF $obj.url!=$url {UPDATE ONLY $obj.id SET url=$url};"
            "};",
            data.get_dict(),
        )

    @get(
        path="/unregister/{service_name:str}",
        security=SECTAG,
        middleware=[jwt_middleware],
        guards=[root_guard],
        raises=[ClientException],
        status_code=204,
    )
    async def unregister(self, service_name: str) -> None:
        resp = await queries.query(
            "BEGIN TRANSACTION;"
            "LET $obj=SELECT VALUE id FROM ONLY type::thing('service',$name);"
            "IF $obj=NONE { THROW 'Service name does not exist: ' + $name };"
            "DELETE ONLY $obj;"
            "COMMIT TRANSACTION;",
            {"name": service_name.lower()},
        )
        if not resp.ok:
            raise ClientException(resp.data)
