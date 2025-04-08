from collections.abc import Callable, Coroutine, Iterable
from datetime import datetime, timezone
from time import time
from typing import Any, LiteralString, Type, overload, override

from db._utils import AllUserData, roles_conv
from db.models import AppUser, DBUser, DBUserData, RegistrationData, UserRolesEnum
from db.strategy._abc import BaseDB
from neo4j import AsyncGraphDatabase, AsyncResult
from utils import hash_password, validate_roles


class NEO4J(BaseDB):
    def __init__(self, uri: str):
        self.driver = AsyncGraphDatabase.driver(uri)

    async def close(self, *args):
        await self.driver.close()

    @overload
    async def _run[
        T
    ](self, query: LiteralString, query_args: dict[str, Any], result: Callable[..., Coroutine[Any, Any, T]]) -> T: ...

    @overload
    async def _run(self, query: LiteralString, query_args: dict[str, Any]) -> None: ...

    async def _run[
        T
    ](
        self,
        query: LiteralString,
        query_args: dict[str, Any],
        result: Callable[..., Coroutine[Any, Any, T]] | None = None,
    ) -> (None | T):
        async with self.driver.session() as db:
            resp = await db.run(query, **query_args)
            return None if result is None else await result(resp)

    @override
    async def create_db(self, min_password_len: int, users: list[dict[str, Any]]) -> None:
        async with self.driver.session() as db:
            for r in UserRolesEnum:
                await db.run("MERGE (:Role {name: $role})", role=r)

        for i in users:
            if len(i["password"]) <= min_password_len:
                raise ValueError(f"Password must be longer than {min_password_len} characters.")
            roles = (UserRolesEnum(x) for x in i["roles"])  # Generator. Insert using one role, then insert rest.
            await self.insert_user(i["name"], hash_password(i["password"]), None, next(roles), "root")
            for role in roles:
                await self.insert_userrole(i["name"], role)

    @override
    async def upsert_token_valid_from_date(self, user: str) -> None:
        query = """\
        MERGE (:User {name: $name})-[t:TOKEN_VALID_FROM]->()
        ON CREATE SET t = {unixtime: $time}
        ON MATCH SET t.unixtime = $time
        """
        await self._run(query, {"name": user, "time": int(time())})

    @override
    async def get_token_valid_from_date(self, user: str) -> int:
        async def results(result: AsyncResult):
            try:
                return int((await result.single(True))["unixtime"])
            except:
                return 0

        query = "MATCH (:User {name: $name})-[t:TOKEN_VALID_FROM]->() RETURN t.unixtime AS unixtime"
        return await self._run(query, {"name": user}, results)

    @override
    async def exists_mail(self, mail: str) -> bool:
        async def results(result: AsyncResult):
            return bool([None async for _ in result])

        return await self._run("MATCH (u:User) WHERE toLower(u.mail)=toLower($mail) RETURN 1", {"mail": mail}, results)

    @override
    async def exists_user(self, name: str, case_insensitive=True) -> bool:
        if case_insensitive:
            query = "MATCH (u:User) WHERE toLower(u.name) = toLower($name) RETURN 1"
        else:
            query = "MATCH (u:User {name: $name}) RETURN 1"

        async def results(result: AsyncResult):
            return bool([None async for _ in result])

        return await self._run(query, {"name": name}, results)

    @override
    async def insert_user(self, user, pwd: bytes, mail: str | None, role: UserRolesEnum, created_by: str) -> None:
        query = """\
        MATCH (r:Role {name: $role})
        MERGE (user:User {name: $name})
        ON CREATE SET user.pwd = $pwd
        MERGE (user)-[:HAS_ROLE]->(r)
        MERGE (user)-[:REGISTRATION_DATA]->(rd:RegistrationData)
        ON CREATE SET rd = $reg_data
        MERGE (user)-[:USER_DATA]->(ud:UserData)
        ON CREATE SET ud = $user_data
        """
        reg_data = RegistrationData.model_construct(
            name=user,
            mail=mail,
            created_by=created_by,
        ).model_dump(mode="json")
        query_args = {
            "role": role.value,
            "name": user,
            "pwd": pwd,
            "reg_data": reg_data,
            "user_data": {
                "display_name": user,
                "mail": mail,
                "created": datetime.now(tz=timezone.utc).isoformat(),
            },
        }
        await self._run(query, query_args)

    @override
    async def delete_user(self, user: str) -> None:
        query = """\
        MATCH
            (a:User {name: $name})-[:USER_DATA]->(b),
            (a)-[:REGISTRATION_DATA]->(c),
            (a)-[d]->()
        DETACH DELETE a, b, c, d
        """
        await self._run(query, {"name": user})

    @override
    async def insert_userrole(self, user: str, role: UserRolesEnum) -> None:
        query = "MATCH (u:User {name: $name}), (r:Role {name: $role}) MERGE (u)-[:HAS_ROLE]->(r)"
        await self._run(query, {"name": user, "role": role.value})

    @override
    async def delete_userrole(self, user: str, role: UserRolesEnum) -> None:
        query = "MATCH (:User {name: $name})-[a:HAS_ROLE]->(:Role {name: $role}) DELETE a"
        await self._run(query, {"name": user, "role": role.value})

    @override
    async def get_user(
        self,
        target_name: str,
        filter_roles: UserRolesEnum | Iterable[UserRolesEnum] = (),
        disjunctive_select: bool = False,
    ) -> DBUser | None:
        query = """\
        MATCH (u:User)
        WHERE toLower(u.name) = toLower($name)
        MATCH (u)-[:HAS_ROLE]->(r:Role)
        RETURN u.name AS name, u.pwd AS pwd, COLLECT(r.name) AS roles
        """

        async def results(result: AsyncResult):
            try:
                res = (await result.single(True)).data()
                res["roles"] = roles_conv(res["roles"])
                if filter_roles and validate_roles(filter_roles, res["roles"], disjunctive_select):
                    return DBUser.model_construct(**res)
            except:
                pass
            return None

        return await self._run(query, {"name": target_name}, results)

    @override
    async def get_app_userdata(
        self,
        target_name: str,
        filter_roles: UserRolesEnum | Iterable[UserRolesEnum] = (),
        disjunctive_select: bool = False,
    ) -> AppUser | None:
        query = """\
        MATCH
            (u:User {name: $name})-[:USER_DATA]->(ud:UserData),
            (u)-[:HAS_ROLE]->(r:Role)
        RETURN u.name AS name, ud.display_name AS display_name, COLLECT(r.name) AS roles
        """

        async def results(result: AsyncResult):
            try:
                res = (await result.single(True)).data()
                res["roles"] = roles_conv(res["roles"])
                if filter_roles and validate_roles(filter_roles, res["roles"], disjunctive_select):
                    return AppUser.model_construct(**res)
            except:
                pass
            return None

        return await self._run(query, {"name": target_name}, results)

    @override
    async def get_db_userdata(self, target_name) -> DBUserData | None:
        """Case insensitive"""
        query = """\
        MATCH (u:User)
        WHERE toLower(u.name) = toLower($name)
        MATCH
            (u)-[:USER_DATA]->(ud:UserData),
            (u)-[:REGISTRATION_DATA]->(reg_data:RegistrationData)
        RETURN u.name AS user, ud.display_name AS display_name, ud.mail AS mail, ud.created AS created, reg_data
        """

        async def results(result: AsyncResult):
            try:
                res = (await result.single(True)).data()
                res["created"] = datetime.fromisoformat(res["created"])
                res["reg_data"] = RegistrationData.model_construct(**res["reg_data"])
                return DBUserData.model_construct(**res)
            except:
                return None

        return await self._run(query, {"name": target_name}, results)

    @override
    async def get_all_users(self, limit=10, offset=0, asc=True) -> list[AllUserData]:
        query = f"""\
        MATCH (u)-[:USER_DATA]->(ud:UserData)
        RETURN u.name AS name, ud.display_name AS display_name, ud.created AS created
        ORDER BY ud.created {'ASC' if asc else 'DESC'}
        SKIP $offset
        LIMIT $limit
        """

        async def results(result: AsyncResult):
            return [AllUserData(**d) async for d in result]

        return await self._run(query, {"limit": limit, "offset": offset}, results)

    @override
    async def select_query[T](self, query, target_name, result_type: Type[T]) -> T | None:
        return None
        # async with self.connect() as db:
        #     async with db.execute(query, (target_name,)) as cursor:
        #         row = await cursor.fetchone()
        #         if row is None:
        #             return None
        # return result_type(**{k: v for k, v in zip(result_type.__annotations__, row)})

    # async def select_query[T](self, query, target_name, result_type: Type[T]) -> T | None:
    #     async with self.connect() as db:
    #         async with db.execute(query, (target_name,)) as cursor:
    #             row = await cursor.fetchone()
    #             if row is None:
    #                 return None
    #     return result_type(**{k: v for k, v in zip(result_type.__annotations__, row)})
    #     return result_type(**{k: v for k, v in zip(result_type.__annotations__, row)})
