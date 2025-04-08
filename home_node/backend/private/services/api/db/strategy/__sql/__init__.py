from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from time import time
from typing import Any, Iterable, Type, override

import orjson as json
from aiosqlite import Cursor, Row, connect
from db._utils import AllUserData, roles_conv
from db.models import AppUser, DBUser, DBUserData, RegistrationData, UserRolesEnum
from db.strategy._abc import BaseDB
from utils import hash_password, validate_roles


class SQL(BaseDB):
    roles_csv = lambda _, rls: roles_conv(rls.split(","))

    def __init__(self, uri: str):
        self.uri = uri

    async def _run_void(self, pre_qry: tuple[tuple[str, None | dict[str, Any]], ...]) -> None:
        async with connect(self.uri) as db:
            for query, query_args in pre_qry:
                await db.execute(query, query_args)
            await db.commit()

    async def _run[T](self, res: Callable[..., Coroutine[Any, Any, T]], qry: str, q_args: dict[str, Any] | None) -> T:
        async with connect(self.uri) as db:
            db.row_factory = Row
            async with db.execute(qry, q_args) as cur:
                return await res(cur)

    @override
    async def create_db(self, min_password_len: int, users: list[dict[str, str]]) -> None:
        """
        Slower to open and close connection for each insert, but it's only done once.
        Re-use code despite slowness, should only run once.
        """
        async with connect(self.uri) as db:
            with open("tables.sql", "r") as f:
                await db.executescript(f.read())

            for i in UserRolesEnum:
                await db.execute("INSERT OR REPLACE INTO Role (name) VALUES (?)", (i.value,))
            await db.commit()

        for i in users:
            if len(i["password"]) <= min_password_len:
                raise ValueError(f"Password must be longer than {min_password_len} characters.")
            roles = (UserRolesEnum(x) for x in i["roles"])  # Generator. Insert using one role, then insert rest.
            await self.insert_user(i["name"], hash_password(i["password"]), None, next(roles), "root")
            for role in roles:
                await self.insert_userrole(i["name"], role)

    @override
    async def upsert_token_valid_from_date(self, user: str) -> None:
        q = """\
        INSERT INTO TokenValidFromDate (user, unixtime)
            VALUES (:user, :unixtime)
        ON CONFLICT (user) DO UPDATE
            SET unixtime = excluded.unixtime
        """
        await self._run_void((("PRAGMA foreign_keys = ON", None), (q, {"user": user, "unixtime": int(time())})))

    @override
    async def get_token_valid_from_date(self, user: str) -> int:
        query = "SELECT unixtime FROM TokenValidFromDate WHERE LOWER(user) = LOWER(:user)"

        async def results(cur: Cursor):
            row = await cur.fetchone()
            return 0 if row is None else int(row["unixtime"])

        return await self._run(results, query, {"user": user})

    @override
    async def exists_mail(self, mail: str) -> bool:
        async def results(cur: Cursor):
            return await cur.fetchone() is not None

        return await self._run(results, "SELECT 1 FROM UserData WHERE LOWER(mail) = LOWER(:mail)", {"mail": mail})

    @override
    async def exists_user(self, name: str, case_insensitive=True) -> bool:
        async def results(cur: Cursor):
            return await cur.fetchone() is not None

        if case_insensitive:
            return await self._run(results, "SELECT 1 FROM User WHERE LOWER(name) = LOWER(:name)", {"name": name})
        return await self._run(results, "SELECT 1 FROM User WHERE name = :name", {"name": name})

    @override
    async def insert_user(self, user, pwd: bytes, mail: str | None, role: UserRolesEnum, created_by: str) -> None:
        query = """\
        INSERT INTO UserData (user, display_name, mail, created, registration_data)
        VALUES (:name, :display_name, :mail, :created, :registration_data)
        """
        query_args = {
            "name": user,
            "display_name": user,
            "mail": mail,
            "created": datetime.now(tz=timezone.utc).isoformat(),
            "registration_data": json.dumps(
                RegistrationData.model_construct(name=user, mail=mail, created_by=created_by).model_dump(mode="json")
            ),
        }
        queries = (
            ("PRAGMA foreign_keys = ON", None),
            ("INSERT INTO User (name, pwd) VALUES (:name, :pwd)", {"name": user, "pwd": pwd}),
            ("INSERT INTO UserRole (user, name) VALUES (:name, :role)", {"name": user, "pwd": role.value}),
            (query, query_args),
        )
        await self._run_void(queries)

    @override
    async def delete_user(self, user: str) -> None:
        query = "DELETE FROM User WHERE name = :name"
        await self._run_void((("PRAGMA foreign_keys = ON", None), (query, {"name": user})))

    @override
    async def insert_userrole(self, user: str, role: UserRolesEnum) -> None:
        query = "INSERT INTO UserRole (user, name) VALUES (:name, :role)"
        await self._run_void((("PRAGMA foreign_keys = ON", None), (query, {"name": user, "role": role.value})))

    @override
    async def delete_userrole(self, user: str, role: UserRolesEnum) -> None:
        query = "DELETE FROM UserRole WHERE user = :name AND name = :role"
        await self._run_void((("PRAGMA foreign_keys = ON", None), (query, {"name": user, "role": role.value})))

    @override
    async def get_user(
        self, target_name: str, filter_roles: UserRolesEnum | Iterable[UserRolesEnum] = (), disjunctive_select: bool = False
    ) -> DBUser | None:
        query = """\
        SELECT usr.name AS name, usr.pwd AS pwd, GROUP_CONCAT(usrrole.name, ",") AS roles
        FROM User usr
        LEFT JOIN UserRole usrrole
            ON usr.name = usrrole.user
        WHERE LOWER(usr.name) = LOWER(:name)
        GROUP BY usr.name, usr.pwd
        """

        async def results(cur: Cursor):
            if row := await cur.fetchone():
                row = dict(row)
                if not row["roles"]:
                    raise ValueError("User has no roles.")
                row["roles"] = self.roles_csv(row["roles"])
                if filter_roles and validate_roles(filter_roles, row["roles"], disjunctive_select):
                    return DBUser.model_construct(**row)
            return None

        return await self._run(results, query, {"name": target_name})

    @override
    async def get_app_userdata(
        self, target_name: str, filter_roles: UserRolesEnum | Iterable[UserRolesEnum] = (), disjunctive_select: bool = False
    ) -> AppUser | None:
        query = """\
        SELECT d.user AS name, d.display_name AS display_name, GROUP_CONCAT(usrrole.name,",") AS roles
        FROM UserData d
        LEFT JOIN UserRole usrrole
            ON d.user = usrrole.user
        WHERE d.user = :name
        GROUP BY usr.name;
        """

        async def results(cur: Cursor):
            if row := await cur.fetchone():
                row = dict(row)
                if row["roles"]:
                    row["roles"] = self.roles_csv(row["roles"])
                    if filter_roles and validate_roles(filter_roles, row["roles"], disjunctive_select):
                        return AppUser.model_construct(**row)
            return None

        return await self._run(results, query, {"name": target_name})

    @override
    async def get_db_userdata(self, target_name) -> DBUserData | None:
        """Case insensitive"""
        query = """
        SELECT user, display_name, mail, created, registration_data
        FROM UserData
        WHERE LOWER(user) = LOWER(:name)
        """

        async def results(cur: Cursor):
            if row := await cur.fetchone():
                row = dict(row)
                row["created"] = datetime.fromisoformat(row["created"])
                row["registration_data"] = RegistrationData.model_construct(**json.loads(row["registration_data"]))
                return DBUserData.model_construct(**row)
            return None

        return await self._run(results, query, {"name": target_name})

    @override
    async def get_all_users(self, limit=10, offset=0, asc=True) -> list[AllUserData]:
        query = (
            "SELECT user, display_name, created FROM UserData"
            f" ORDER BY created {'ASC' if asc else 'DESC'} LIMIT {limit} OFFSET {offset}"
        )

        async def results(cur: Cursor):
            return [AllUserData(**row) for row in await cur.fetchall()]

        return await self._run(results, query, None)

    @override
    async def select_query[T](self, query, target_name, result_type: Type[T]) -> T | None:
        async with connect(self.uri) as db:
            async with db.execute(query, (target_name,)) as cursor:
                row = await cursor.fetchone()
                if row is None:
                    return None
        return result_type(**{k: v for k, v in zip(result_type.__annotations__, row)})
