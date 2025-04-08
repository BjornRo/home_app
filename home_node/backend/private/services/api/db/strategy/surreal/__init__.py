__import__("sys").path.append("/")  # To import from appdata. "/" for linting
import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict, override

from asyncio_connection_pool import ConnectionPool, ConnectionStrategy
from constants import DATETIME_MAX, DATETIME_MIN
from db.internal.models import (
    InternalRolesEnum,
    InternalUser,
    InternalUserAPIRegistration,
    InternalUserLogin,
    InternalUserRegistration,
    InternalUserRoles,
    InternalUserUpdate,
    InternalUserView,
    TableInternal,
)
from db.models import (
    AllUserView,
    AppUser,
    LoginTEnum,
    TableAPI,
    User,
    UserData,
    UserLogin,
    UserRegistration,
    UserRolesAPIStruct,
    UserRolesEnum,
)
from db.strategy.myabc import BaseDB, BaseInternalDB
from litestar.exceptions import ClientException, InternalServerException
from msgspec import convert, to_builtins
from mytypes import (
    DateT,
    DateTimeUTC,
    ItemAlreadyExistException,
    Password,
    UserID,
    UserID_Result,
)
from utils import (
    datetime_now_utc_isoformat,
    datetime_to_isoformat,
    generate_created_end_date,
    validate_guid,
    validate_mail,
    validate_name,
)

from appdata.surreal import Surreal


class Role(TypedDict):
    name: UserRolesEnum


class SurrealPool(ConnectionStrategy):
    __slots__ = ("url", "ns", "db", "connection_timeout")

    def __init__(
        self, url: str, database: str, namespace: str, connection_timeout: timedelta | None = timedelta(minutes=10)
    ):
        self.url = url
        self.ns, self.db = namespace, database
        self.connection_timeout = connection_timeout

    async def make_connection(self) -> Surreal:
        db = await Surreal().connect(self.url, idle_timeout=self.connection_timeout)
        await db.use(namespace=self.ns, database=self.db)
        return db

    def connection_is_closed(self, conn: Surreal) -> bool:
        return conn.closed()

    async def close_connection(self, conn: Surreal) -> None:
        conn.is_closing = True
        await conn.close()


class SurrealSimple:
    __slots__ = ("pool",)

    def __init__(self, uri: str, database: str, namespace="app"):
        self.pool = ConnectionPool[Surreal](
            strategy=SurrealPool(uri, database=database, namespace=namespace),
            max_size=20,
            burst_limit=200,
        )

    async def query(self, query: str, query_args: dict[str, Any] | None = None):
        async with self.pool.get_connection() as db:
            return await db.query(query, query_args)


class SurrealInternalDB(BaseInternalDB, SurrealSimple):
    @override
    async def insert_internal_user(
        self,
        name: str,
        hash_b64_pwd: str,
        created_by_user_id: str,
        enabled=True,
    ) -> None | UserID:
        regdata = InternalUser(
            enabled=enabled,
            login=InternalUserLogin(name=name.lower(), pwd=hash_b64_pwd),
            registration=InternalUserRegistration(
                created_by=f"{TableInternal.USER}:{created_by_user_id}",
                created=datetime.now(UTC),
            ),
        )
        resp = await self.query(
            f"CREATE ONLY {TableInternal.USER} CONTENT $data RETURN VALUE meta::id(id)",
            {"data": to_builtins(regdata)},
        )
        if resp.ok:  # In case of name exists
            return resp.data
        raise ClientException(resp.data)

    @override
    async def insert_internal_userrole(
        self,
        name_or_user_id: str,
        role: InternalRolesEnum,
        given_by_user_id: str,
    ) -> bool:
        r = TableInternal.USER_ROLE
        u = TableInternal.USER
        qry = (
            f"LET $x=(SELECT VALUE id FROM ONLY {u} WHERE login.name=string::lowercase($name) LIMIT 1) OR fn::tab_str('{u}',$name);"
            "LET $uid=SELECT VALUE id FROM ONLY $x;"
            f"IF $uid {{(CREATE ONLY {r}:{{id:$uid,role:'{role}'}} SET given_by={u}:{given_by_user_id})}} ELSE {{Throw ''}}"
        )
        return (await self.query(qry, {"name": name_or_user_id})).ok

    @override
    async def get_all_internal_user_view(
        self,
        limit: int,
        offset: int,
        asc: bool,
    ) -> list[UserID_Result[InternalUserView]]:
        qry = (
            "SELECT VALUE ["
            "  meta::id(id)"
            "  ,{"
            "   name:login.name"
            "   ,created:registration.created"
            "   ,created_by:registration.created_by"
            "   ,enabled:enabled"
            f"  ,roles:(SELECT VALUE id.role FROM {TableInternal.USER_ROLE} WHERE id.id=id)"
            "  }"
            f"] FROM {TableInternal.USER} ORDER BY registration.created "
            f"{'ASC' if asc else 'DESC'} LIMIT {limit} START {offset}"
        )
        return [(user_id, convert(data, type=InternalUserView)) for user_id, data in (await self.query(qry)).data]

    @override
    async def get_internal_userlogin(self, name: str) -> UserID_Result[InternalUserAPIRegistration] | None:
        resp = await self.query(
            "SELECT VALUE [meta::id(id),{name:login.name,pwd:login.pwd,enabled:enabled}]"
            f" FROM ONLY {TableInternal.USER} WHERE login.name=string::lowercase($name) LIMIT 1",
            {"name": name},
        )
        return resp.data

    @override
    async def get_internal_userroles(self, user_id: str) -> InternalUserRoles:
        resp = await self.query(f"SELECT VALUE id.role FROM {TableInternal.USER_ROLE} WHERE id.id=user:{user_id}")
        return InternalUserRoles(roles=InternalRolesEnum.convert(resp.data))

    @override
    async def get_internal_token_valid_from_date(self, user_id: str) -> DateTimeUTC:
        result = (await self.query(f"{TableInternal.TOKEN_VALID_FROM}:{user_id}.date")).data
        return datetime.fromisoformat(result) if result else DATETIME_MIN

    @override
    async def upsert_internal_token_valid_from_date(self, user_id: str) -> None:
        await self.query(
            f"INSERT INTO {TableInternal.TOKEN_VALID_FROM} (id,date)"
            f" VALUES ({TableInternal.USER}:{user_id},$date) ON DUPLICATE KEY UPDATE date=$date",
            {"date": datetime_now_utc_isoformat()},
        )

    @override
    async def update_internal_user(self, name_or_user_id: str, data: InternalUserUpdate) -> None:
        if not data:
            raise ClientException("No data given")
        t = TableInternal.USER
        qry_kw = {}
        qry = [
            f"LET $x=(SELECT VALUE id FROM ONLY {t} WHERE login.name=string::lowercase($nuid) LIMIT 1) OR fn::tab_str('{t}',$nuid);"
            "LET $uid=SELECT VALUE id FROM ONLY $x;"  # If user does not exist, update None which does nothing
            "UPDATE $uid SET "
        ]
        update = []
        if value := data.get("enabled"):
            update.append(f"enabled=$enabled")
            qry_kw["enabled"] = value

        if value := data.get("name"):
            update.append(f"login.name=$name")
            qry_kw["name"] = value.lower()

        if value := data.get("pwd"):
            update.append(f"login.pwd=$pwd")
            qry_kw["pwd"] = value

        qry.append(",".join(update))

        resp = await self.query("".join(qry), {"nuid": name_or_user_id} | qry_kw)
        if not resp.ok:  # UPDATE None Throws error in db
            raise ClientException(resp.data)

    @override
    async def exists_internal_user(self, user_id: str) -> bool:
        return (await self.query(f"SELECT VALUE 1 FROM ONLY {TableInternal.USER}:{user_id}")) is not None

    @override
    async def search_internal_user(
        self, name_or_user_id: str, limit: int, exact_match: bool
    ) -> list[UserID_Result[InternalUserView]]:
        query = [
            "SELECT VALUE ["
            " meta::id(id),"
            " {"
            "  name:login.name,"
            "  created:registration.created,"
            "  created_by:registration.created_by,"
            "  enabled:enabled,"
            f" roles:(SELECT VALUE id.role FROM {TableInternal.USER_ROLE} WHERE id.id=id)"
            " }"
            "] FROM"
        ]
        PREP_STM_KEY = "x"
        f = lambda x: f"{x}=${PREP_STM_KEY}" if exact_match else f"string::contains({x},${PREP_STM_KEY})"

        or_clauses = [f("login.name")]
        try:
            validate_guid(name_or_user_id, exact_len=exact_match)
            or_clauses.append(f("meta::id(id)"))
        except:
            pass
        query.append(" OR ".join(or_clauses))
        query.append("ORDER BY registration.created ASC")
        if limit > 0:
            query.append(f"LIMIT {limit}")
        resp = await self.query(" ".join(query), {PREP_STM_KEY: name_or_user_id.lower()})
        return [(user_id, convert(data, type=InternalUserView)) for user_id, data in resp.data]

    @override
    async def delete_internal_user(self, name_or_user_id: str) -> bool:
        table = TableInternal.USER
        qry = f"DELETE ONLY {table} WHERE login.name=string::lowercase($name) OR id=fn::tab_str('{table}',$name) RETURN BEFORE"
        return (await self.query(qry, {"name": name_or_user_id})).ok

    @override
    async def delete_internal_userrole(self, name_or_user_id: str, role: InternalRolesEnum) -> bool:
        user = TableInternal.USER
        urole = TableInternal.USER_ROLE
        qry = (
            f"LET $uid=(SELECT VALUE id FROM ONLY {user} WHERE login.name=$x LIMIT 1) OR meta::id(id)=$x);"
            f"DELETE ONLY {urole} WHERE id.id=fn::tab_rec('{urole}',$uid) AND id.role='{role}' RETURN BEFORE"
        )
        return (await self.query(qry, {"x": name_or_user_id.lower()})).ok


class SurrealDB(BaseDB, SurrealSimple):
    @staticmethod
    def _get_all_userview_base_query():
        return (
            "SELECT"
            " meta::id(id) AS user_id,"
            " (SELECT VALUE meta::id(out.id) FROM $parent.id->has_role) AS roles,"
            " (SELECT meta::id(out) AS resource, rwx, start, end, given_by, created FROM $parent.id->has_service) AS acl,"
            " * OMIT id "
            f"FROM {TableAPI.USER}"
        )

    @override
    async def get_all_user_view(self, limit=10, offset=0, asc=True) -> list[AllUserView]:
        resp = await self.query(
            self._get_all_userview_base_query()
            + f" ORDER BY registration.created {'ASC' if asc else 'DESC'} LIMIT {limit} START {offset}"
        )
        return [convert(r, type=AllUserView) for r in resp.data]

    @override
    async def insert_user(
        self,
        name: str,
        mail: str | None,
        hash_b64_pwd: str,
        created_by_user_id: str,
        role: UserRolesEnum,
    ) -> UserID | None:
        date = datetime.now(UTC)
        new_user = to_builtins(
            User(
                modified_date=date,
                login=UserLogin(
                    name=name.lower(),
                    pwd=hash_b64_pwd,
                    mail=mail.lower() if mail else None,
                ),
                registration=UserRegistration(
                    created_by=f"{TableAPI.USER}:{created_by_user_id}",
                    created=date,
                    number=0,
                    name=name,
                    mail=mail,
                ),
                data=UserData(
                    name=name,
                ),
            )
        )
        max_date = datetime_to_isoformat(DATETIME_MAX)
        created: str = new_user["modified_date"]
        role_given_by = "root"
        qry = (
            "BEGIN TRANSACTION;"
            "LET $num=UPDATE ONLY counter:user SET value += 1 RETURN VALUE value;"
            f"LET $uid=CREATE ONLY {TableAPI.USER} CONTENT $data RETURN VALUE id;"
            "UPDATE ONLY $uid SET registration.number=$num;"
            f"LET $role=RELATE ONLY $uid->has_role->{TableAPI.USER_ROLE}:{role}"
            f" SET from='{created}',to='{max_date}',given_by={TableAPI.USER}:{role_given_by},created='{created}';"
            "IF !($uid AND $role) {THROW 'Fail';} ELSE {RETURN meta::id($uid);};"
            "COMMIT TRANSACTION;"
        )
        resp = await self.query(qry, {"data": new_user})
        if resp.ok:
            return resp.data
        raise ClientException(resp.data)

    @override
    async def replace_userrole(
        self, user_id: str, role: UserRolesEnum, to_replace: UserRolesEnum, end_date: DateT, given_by_user_id: str
    ):
        created, _end_date = generate_created_end_date(end_date, datetime.now(UTC))
        user_t = f"{TableAPI.USER}:{user_id}"
        resp = await self.query(
            "BEGIN TRANSACTION;"
            f"LET $to_repl=SELECT VALUE 1 FROM ONLY {user_t}->has_role WHERE out={TableAPI.USER_ROLE}:{role} LIMIT 1;"
            "IF $to_repl=1 {THROW 'User already have role'};"
            f"LET $role=DELETE ONLY {user_t}->has_role WHERE out={TableAPI.USER_ROLE}:{to_replace} RETURN BEFORE"
            "IF $role=None {THROW 'User does not have role to be replaced with'};"
            f"RELATE ONLY {user_t}->has_role->{TableAPI.USER_ROLE}:{role}"
            f" SET from='{created}',to='{_end_date}',given_by={TableAPI.USER}:{given_by_user_id},created='{created}';"
            "COMMIT TRANSACTION;"
        )
        if not resp.ok:
            raise InternalServerException(resp.data)

    @override
    async def insert_userrole(self, user_id: str, role: UserRolesEnum, end_date: DateT, given_by_user_id: str) -> None:
        created, _end_date = generate_created_end_date(end_date, datetime.now(UTC))
        user_t = f"{TableAPI.USER}:{user_id}"
        new_role = f"{TableAPI.USER_ROLE}:{role}"
        resp = await self.query(
            "BEGIN TRANSACTION;"
            f"LET $to_repl=SELECT VALUE 1 FROM ONLY {user_t}->has_role WHERE out={new_role} LIMIT 1;"
            "IF $to_repl=1 {THROW 'User already have role'};"
            f"RELATE ONLY {user_t}->has_role->{new_role}"
            f" SET from='{created}',to='{_end_date}',given_by={TableAPI.USER}:{given_by_user_id},created='{created}';"
            "COMMIT TRANSACTION;"
        )
        if not resp.ok:
            raise InternalServerException(resp.data)

    @override
    async def get_app_user(
        self,
        user_id: str,
        filter_roles: Iterable[UserRolesEnum] = (),
        disjunctive_select=False,
    ) -> AppUser | None:
        user_thing = f"{TableAPI.USER}:{user_id}"
        qry = (
            f"LET $roles=SELECT VALUE meta::id(out.id) FROM {user_thing}->has_role;"
            f"SELECT VALUE [data.name,$roles] FROM ONLY {user_thing}"
        )
        data: None | tuple[str, list[str]] = (await self.query(qry)).data
        if data:
            name, roles = data
            appuser = AppUser(name=name, roles=UserRolesEnum.convert(roles))
            if not appuser.roles:
                raise InternalServerException
            if appuser.filter_roles(filter_roles, disjunctive_select):
                return appuser
        return None

    @override
    async def get_user(self, user_id: str) -> User | None:
        data = (await self.query(f"SELECT * FROM ONLY {TableAPI.USER}:{user_id}")).data
        return None if data is None else convert(data, type=User)

    @override
    async def get_user_name(self, user_id: str) -> str | None:
        return (await self.query(f"SELECT VALUE login.name FROM ONLY {TableAPI.USER}:{user_id}")).data

    @override
    async def get_user_modified(self, user_id: str) -> DateTimeUTC | None:
        data = (await self.query(f"SELECT VALUE modified_date FROM ONLY {TableAPI.USER}:{user_id}")).data
        return None if data is None else datetime.fromisoformat(data)

    @override
    async def get_user_id(self, name: str) -> str | None:
        qry = f"SELECT VALUE meta::id(id) FROM ONLY {TableAPI.USER} WHERE login.name=string::lowercase($mykey) LIMIT 1"
        return (await self.query(qry, {"mykey": name})).data

    @override
    async def get_userid_roles_pwd(
        self,
        login: str,
        login_type: LoginTEnum,
        filter_roles: Iterable[UserRolesEnum] = (),
        disjunctive_select=False,
    ) -> UserID_Result[tuple[Password, UserRolesAPIStruct]] | None:
        if not login:
            return None

        match login_type:
            case LoginTEnum.NAME:
                lt = LoginTEnum.NAME
            case LoginTEnum.MAIL:
                if not (len(s := login.split("@")) == 2 and "." in s[1]):
                    return None
                lt = LoginTEnum.MAIL

        qry = (  # 3.12 supports f-strings with same quotation. Black formatter does not :(
            "SELECT VALUE [meta::id(id), login.pwd, (SELECT VALUE meta::id(out.id) FROM $parent.id->has_role)] "
            f"FROM ONLY {TableAPI.USER} WHERE login.{lt}=string::lowercase($mykey) LIMIT 1"
        )

        data = (await self.query(qry, {"mykey": login})).data
        if data:
            user_id, password, roles = data
            user_roles = UserRolesAPIStruct(roles=UserRolesEnum.convert(roles))
            if user_roles.filter_roles(filter_roles, disjunctive_select):
                return user_id, (password, user_roles)
        return None

    @override
    async def get_user_login(self, user_id: str) -> UserLogin | None:
        return (await self.query(f"SELECT name,pwd,mail FROM ONLY {TableAPI.USER}:{user_id}.login")).data

    @override
    async def get_user_data(self, user_id: str) -> UserData | None:
        if data := (await self.query(f"SELECT * FROM ONLY {TableAPI.USER}:{user_id}.data")).data:
            return convert(data, type=UserData)
        return None

    @override
    async def get_user_registration(self, user_id: str) -> UserRegistration | None:
        if data := (await self.query(f"SELECT * FROM ONLY {TableAPI.USER}:{user_id}.registration")).data:
            return convert(data, type=UserRegistration)
        return None

    @override
    async def update_name(self, user_id: str, new_login: str) -> None:
        qry = (
            "BEGIN TRANSACTION;"
            "LET $uid = SELECT VALUE True FROM user WHERE login.name=$name;"
            f"IF $uid {{Throw ''}} ELSE {{(UPDATE ONLY {TableAPI.USER}:{user_id} SET login.name=$name)}};"
            "COMMIT TRANSACTION;"
        )
        if (await self.query(qry, {"name": new_login.lower()})).ok:
            return None
        raise ItemAlreadyExistException

    @override
    async def update_mail(self, user_id: str, new_mail: str) -> None:
        qry = (
            "BEGIN TRANSACTION;"
            "LET $uid = SELECT VALUE True FROM user WHERE login.mail=string::lowercase($mail);"
            f"IF $uid {{Throw ''}} ELSE {{(UPDATE ONLY {TableAPI.USER}:{user_id} SET login.mail=$mail)}};"
            "COMMIT TRANSACTION;"
        )
        if (await self.query(qry, {"mail": new_mail.lower()})).ok:
            return None
        raise ItemAlreadyExistException

    @override
    async def update_data_name(self, user_id: str, new_name: str) -> None:
        await self.query(f"UPDATE ONLY {TableAPI.USER}:{user_id} SET data.name=$name", {"name": new_name})

    @override
    async def update_pwd(self, user_id: str, new_hash_b64_pwd: str) -> None:
        await self.query(f"UPDATE ONLY {TableAPI.USER}:{user_id} SET pwd=$pwd", {"pwd": new_hash_b64_pwd})

    @override
    async def update_user_modified(self, user_id: str, date: DateTimeUTC) -> None:
        await self.query(f"UPDATE ONLY {TableAPI.USER}:{user_id} SET modified_date='{datetime_to_isoformat(date)}'")

    @override
    async def get_token_valid_from_date(self, user_id: str) -> DateTimeUTC:
        data = (await self.query(f"{TableAPI.TOKEN_VALID_FROM}:{user_id}.date")).data
        return datetime.fromisoformat(data) if data else DATETIME_MIN

    @override
    async def upsert_token_valid_from_date(self, user_id: str) -> None:
        await self.query(
            f"INSERT INTO {TableAPI.TOKEN_VALID_FROM} (id,date)"
            f" VALUES ({TableAPI.USER}:{user_id},$date) ON DUPLICATE KEY UPDATE date=$date",
            {"date": datetime_now_utc_isoformat()},
        )

    @override
    async def exists_mail(self, mail: str) -> bool:
        resp = await self.query(
            f"SELECT VALUE 1 FROM ONLY {TableAPI.USER} WHERE login.mail=string::lowercase($mail) LIMIT 1",
            {"mail": mail},
        )
        return resp.data is not None

    @override
    async def exists_name(self, name: str) -> bool:
        resp = await self.query(
            f"SELECT VALUE 1 FROM ONLY {TableAPI.USER} WHERE login.name=string::lowercase($name) LIMIT 1",
            {"name": name},
        )
        return resp.data is not None

    @override
    async def exists_user_id(self, user_id: str) -> bool:
        resp = await self.query(f"SELECT VALUE 1 FROM ONLY {TableAPI.USER}:{user_id}")
        return resp.data is not None

    @override
    async def search_user(self, name_or_email: str, limit: int, exact_match: bool = False) -> list[AllUserView]:
        if limit < 0:
            raise ClientException("Invalid limit given")
        query = [self._get_all_userview_base_query(), "WHERE"]

        PREP_STM_KEY = "x"
        f = lambda x: f"{x}=${PREP_STM_KEY}" if exact_match else f"string::contains({x},${PREP_STM_KEY})"

        if "@" in name_or_email:
            if exact_match:
                validate_mail(name_or_email)
            query.append(f("login.mail"))
        else:
            or_clauses = []
            try:
                validate_guid(name_or_email, exact_len=exact_match)
                or_clauses.append(f("meta::id(id)"))
            except:
                pass
            try:
                validate_name(name_or_email)
                or_clauses.append(f("login.name"))
            except:
                pass
            if not or_clauses:
                raise ClientException("Invalid input given")
            query.append(" OR ".join(or_clauses))
        if limit:
            query.append(f"LIMIT {limit}")

        data = (await self.query(" ".join(query), {PREP_STM_KEY: name_or_email.lower()})).data
        return [convert(r, type=AllUserView) for r in data]

    @override
    async def delete_user(self, user_id: str) -> None:
        ignore = [TableAPI.USER_ROLE]  # From testing, relations are deleted if no target/src, nice :)
        for table in TableAPI:
            if table not in ignore:
                await self.query(f"DELETE {table}:{user_id}")

    @override
    async def delete_userrole(self, user_id: str, role: UserRolesEnum) -> None:
        await self.query(f"DELETE {TableAPI.USER}:{user_id}->has_role WHERE out={TableAPI.USER_ROLE}:{role}")

    @override
    async def delete_mail(self, user_id: str) -> None:
        qry = (
            f"LET $uid={TableAPI.USER}:{user_id};"
            "IF (SELECT VALUE 1 FROM ONLY $uid) {UPDATE ONLY $uid SET login.mail=null} ELSE {THROW ''};"
        )
        if not (await self.query(qry)).ok:
            raise InternalServerException

    """Misc"""

    @override
    async def number_of_users(self) -> int:
        return (await self.query("SELECT VALUE c FROM (SELECT count() as c FROM user GROUP ALL)")).data.pop()
