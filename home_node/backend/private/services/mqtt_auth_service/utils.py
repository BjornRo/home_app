from __future__ import annotations

__import__("sys").path.append("/")  # To import from appdata. "/" for linting
import asyncio
import base64
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from enum import StrEnum
from typing import TypedDict

from bcrypt import checkpw as _checkpw

from appdata.surreal import Surreal


async def checkpw(pwd: bytes, hash: bytes, pool=ProcessPoolExecutor(2)) -> bool:
    return await asyncio.get_event_loop().run_in_executor(pool, _checkpw, pwd, hash)


class InternalRolesEnum(StrEnum):
    MQTT = "mqtt"
    LOCAL = "local"
    GLOBAL = "global"
    HOME = "home"
    REMOTE = "remote"
    API = "api"

    @staticmethod
    def convert(roles: list[str] | list[InternalRolesEnum]) -> list[InternalRolesEnum]:
        return [InternalRolesEnum(r) for r in roles]


class UserIDPwd(TypedDict):
    id: str
    name: str
    pwd: str
    enabled: bool
    roles: list[InternalRolesEnum]


class SurrealDB:
    __slots__ = ("_db", "ns", "db", "uri")
    _fake_pw = "JDJiJDEyJEU5Q0U3azFlcHdZTjkuQkwuSWZMemVucWYuTWF1dzRGS0c3aVExUjZnRmFtd3dnSHJycXNp"

    def __init__(self, uri: str, database, namespace="app"):
        self.uri = uri
        self._db = Surreal()
        self.ns = namespace
        self.db = database

    async def auth_user(self, name: str, pwd: str, filter_roles: Iterable[InternalRolesEnum] = ()) -> bool:
        _filter_roles = "','".join((*filter_roles, InternalRolesEnum.MQTT))
        qry = (  # 3.12 supports f-strings with same quotation. Black formatter does not :(
            "SELECT * FROM ONLY (SELECT"
            " login.name AS name,"
            " login.pwd AS pwd,"
            " meta::id(id) AS id,"
            " enabled,"
            " (SELECT VALUE id.role FROM user_role WHERE id.id=$parent.id) AS roles"
            " FROM ONLY user WHERE login.name=string::lowercase($mykey) LIMIT 1"
            f") WHERE ['{_filter_roles}'] ALLINSIDE roles"
        )
        async with await self._db.connect(self.uri) as db:
            await db.use(namespace=self.ns, database=self.db)
            dbusr: UserIDPwd | None = (await db.query(qry, {"mykey": name})).data

        h64 = dbusr["pwd"] if dbusr else self._fake_pw
        return await checkpw(pwd.encode(), base64.b64decode(h64)) and dbusr is not None and dbusr["enabled"]
