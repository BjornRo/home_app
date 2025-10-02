from __future__ import annotations

import asyncio
import base64
from concurrent.futures import ProcessPoolExecutor
from typing import Iterable

import aiosqlite
from bcrypt import checkpw as _checkpw

from appdata.internal_shared import InternalRolesEnum


async def checkpw(pwd: bytes, hash: bytes, pool=ProcessPoolExecutor(2)) -> bool:
    return await asyncio.get_event_loop().run_in_executor(pool, _checkpw, pwd, hash)


class SQLDB:
    _fake_pw = "JDJiJDEyJEU5Q0U3azFlcHdZTjkuQkwuSWZMemVucWYuTWF1dzRGS0c3aVExUjZnRmFtd3dnSHJycXNp"
    __slots__ = ("file",)

    def __init__(self, file: str):
        self.file = file

    async def auth_user(self, name: str, pwd: str, filter_roles: Iterable[InternalRolesEnum] = ()) -> bool:
        required_roles = (*filter_roles, InternalRolesEnum.MQTT)
        roles_sql = ",".join(f"'{role}'" for role in required_roles)

        query = (
            "  SELECT u.pwd, u.enabled"
            "   FROM user u"
            "  JOIN has_role hr ON hr.user_id = u.user_id"
            "  WHERE u.user_id = ? AND u.enabled = 1"
            f"  AND hr.role_name IN ({roles_sql})"
            "  GROUP BY u.pwd, u.enabled"
            f" HAVING COUNT(DISTINCT hr.role_name) = {len(required_roles)}"
            "  LIMIT 1"
        )

        async with aiosqlite.connect(self.file) as db:
            async with db.execute(query, (name,)) as cursor:
                row = await cursor.fetchone()

        hash64: str = row[0] if row else self._fake_pw
        return await checkpw(pwd.encode(), base64.b64decode(hash64)) and bool(pwd)
