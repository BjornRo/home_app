from typing import Any, Iterable, Literal, TypedDict, Unpack

import aiosqlite
import msgspec
from core import exceptions, models, types
from storage.db import tables
from storage.db.sql.sqlite import SQLite
from utils import helpers, time_helpers, validation

from appdata import shared  # type: ignore

from . import update_fields

type UserColumnFetch = Literal["login_mail", "login_name", "user_id"]


class UserUpdateFields(TypedDict, total=False):
    login_name: str
    login_mail: str | None
    password: str


class UserAccountRepository(msgspec.Struct, gc=False):
    db: SQLite

    # region: Create
    async def create_user(
        self,
        login_name: str,
        login_mail: str | None,
        password_hash: str,
        enabled: bool,
        created_by: types.UserID | None = None,
    ) -> types.UserID:
        """
        Raises:
            IntegrityError: if value already exists
        """
        user_id = helpers.uuid7()  # TODO replace with std in python>=3.14
        min_time = time_helpers.DATETIME_MIN_STR

        try:
            async with self.db.connect() as conn:
                await conn.execute(
                    f"INSERT INTO {tables.User.__name__}"
                    " (user_id, login_name, login_mail, password, enabled, last_login_date, last_updated_date)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (user_id, login_name, login_mail, password_hash, enabled, min_time, min_time),
                )
                await conn.execute(
                    f"INSERT INTO {tables.Registration.__name__}"
                    " (user_id, name, mail, created_by, created_date)"
                    " VALUES (?,?,?,?,?)",
                    (user_id, login_name, login_mail, created_by, shared.datetime_now_isofmtZ()),
                )
                await conn.execute(
                    f"INSERT INTO {tables.User_Profile.__name__}"
                    " (user_id, display_name, last_updated_date)"
                    " VALUES (?,?,?)",
                    (user_id, login_name, min_time),
                )
                await conn.commit()
                return user_id
        except aiosqlite.IntegrityError as e:
            raise exceptions.IntegrityError(str(e)) from e
        except Exception as e:
            shared.print_err(e)
            raise

    # endregion
    # region: Read
    async def get_user(self, method: UserColumnFetch, value: str):
        """
        Raises:
            NotFoundError: if name or mail does not exist
        """
        query = f"SELECT * FROM {tables.User.__name__} WHERE {method} = ?"
        if row := await self.db.fetch_one(query, (value,)):
            return msgspec.convert(row, type=tables.User, strict=False)
        raise exceptions.NotFoundError

    async def get_user_registration(self, user_id: types.UserID):
        """
        Raises:
            NotFoundError: if name or mail does not exist
        """
        query = f"SELECT * FROM {tables.Registration.__name__} WHERE user_id = ?"
        if row := await self.db.fetch_one(query, (user_id,)):
            return msgspec.convert(row, type=tables.Registration)
        raise exceptions.NotFoundError

    async def exists_user(self, method: UserColumnFetch, value: str) -> bool:
        query = f"SELECT 1 FROM {tables.User.__name__} WHERE {method} = ? LIMIT 1"
        return await self.db.fetch_one(query, (value,)) is not None

    # endregion
    # region: Update
    async def update_user_enabled(self, user_id: types.UserID, enable: bool):
        query = f"UPDATE {tables.User.__name__} SET enabled = ? WHERE user_id = ?"
        await self.db.execute_void(query, (enable, user_id))

    async def update_user_login_date(self, user_id: types.UserID):
        query = f"UPDATE {tables.User.__name__} SET last_login_date = ? WHERE user_id = ?"
        await self.db.execute_void(query, (shared.datetime_now_isofmtZ(), user_id))

    async def update_user(self, user_id: types.UserID, **fields: Unpack[UserUpdateFields]):
        """
        Raises:
            UserInputError: if no fields are supplied
            IntegrityError: if value already exists
        """
        await update_fields(db=self.db, table=tables.User.__name__, user_id=user_id, **fields)

    # endregion
    # region: Delete
    async def delete_user(self, user_id: types.UserID):
        query = f"DELETE FROM {tables.User.__name__} WHERE user_id = ?"
        await self.db.execute_void(query, (user_id,))

    # endregion
    # region: Misc
    async def search_user(
        self,
        name_or_email: str,
        limit: int | None,
        offset: int | None = None,
        exact_match=False,
    ) -> list[models.AllUserView]:
        if "@" in name_or_email:
            if exact_match:
                validation.validate_mail(name_or_email)
                where_clause = "u.login_mail = :term"
            else:
                where_clause = "u.login_mail LIKE :term"
        else:
            validation.validate_name(name_or_email)
            if exact_match:
                where_clause = "u.login_name = :term"
            else:
                where_clause = "u.login_name LIKE :term OR u.login_mail LIKE :term"

        selections = [f"WHERE {where_clause}"]
        if limit is not None:
            selections.append(f"LIMIT {limit}")
        if offset is not None:
            selections.append(f"OFFSET {offset}")

        query = __get_alluserview_base_query(" ".join(selections))
        param = {"term": name_or_email if exact_match else f"%{name_or_email}%"}

        rows = await self.db.fetch_all(query, param)
        return __alluserview_query_rows_to_struct(rows)

    async def get_alluserview(self, limit=10, offset=0, asc=True) -> list[models.AllUserView]:
        query = __get_alluserview_base_query(f"ORDER BY reg.created_date {"ASC" if asc else "DESC"} LIMIT ? OFFSET ?")

        rows = await self.db.fetch_all(query, (limit, offset))
        return __alluserview_query_rows_to_struct(rows)


def __get_alluserview_base_query(query_filter: str = ""):
    """
    `Tables`:
        `reg`: Registration
        `u`: User
    """
    return (
        " WITH roles_agg AS ("
        "   SELECT user_id, json_group_array(role_name) AS roles"
        f"  FROM {tables.Has_Role.__name__}"
        "   GROUP BY user_id"
        " ),"
        " services_agg AS ("
        "   SELECT user_id, json_group_object(LOWER(service_name), rwx) AS acl"
        f"  FROM {tables.Has_Service.__name__}"
        "   GROUP BY user_id"
        " ),"
        " paged_users AS ("
        "    SELECT u.user_id, u.login_name, u.login_mail, u.enabled,"
        "      reg.created_date as registration_date,"
        "      reg.created_by AS created_by"
        f"   FROM {tables.User.__name__} u"
        f"   LEFT JOIN {tables.Registration.__name__} reg ON u.user_id = reg.user_id"
        f"   {query_filter}"
        " )"
        " SELECT"
        "  u.user_id,"
        "  u.enabled,"
        "  u.registration_date,"
        "  up.display_name,"
        "  u.login_name,"
        "  u.login_mail,"
        "  u.created_by,"
        "  COALESCE(s.acl, '[]') AS services,"
        "  COALESCE(r.roles, '[]') AS roles"
        " FROM paged_users u"
        " LEFT JOIN roles_agg r ON u.user_id = r.user_id"
        " LEFT JOIN services_agg s ON u.user_id = s.user_id "
        f"LEFT JOIN {tables.User_Profile.__name__} up ON u.user_id = up.user_id"
    )


# decode=msgspec.json.Decoder().decode
def __alluserview_query_rows_to_struct(rows: Iterable[dict[str, Any]]):
    def apply(row: dict[str, Any]):
        # for key in ("services", "roles"):
        #     row[key] = decode(row[key])
        return msgspec.convert(row, type=models.AllUserView, strict=False)

    return [apply(row) for row in rows]


"""
def _get_detailed_all_userview_base_query(self):
    partial_query = (
        "  WITH roles_agg AS ("
        "    SELECT user_id, json_group_array(DISTINCT role_name) AS roles"
        f"   FROM {tables.Has_Role.__name__}"
        "    GROUP BY user_id"
        "  ),"
        "  services_agg AS ("
        "    SELECT user_id, json_group_array(json_object("
        "      'service_name', service_name,"
        "      'rwx', rwx,"
        "      'valid_from', valid_from,"
        "      'valid_to', valid_to,"
        "      'given_by', given_by,"
        "      'created_date', created_date"
        "    )) AS acl"
        f"   FROM {tables.Has_Service.__name__}"
        "    GROUP BY user_id"
        "  ),"
        "  paged_users AS ("
        "     SELECT u.last_updated_date, u.user_id, u.login_name, u.login_mail, u.password"
        "       reg.name AS registration_name,"
        "       reg.mail AS registration_mail,"
        "       reg.created_date as registration_created_date,"
        "       reg.created_by AS registration_created_by,"
        f"    FROM {tables.User.__name__} u"
        f"    LEFT JOIN {tables.Registration.__name__} reg ON u.user_id = reg.user_id"
        "     {fmt} "  # NOTE Use .format(fmt=...)!
        "  )"
        "  SELECT u.last_updated_date, u.user_id, u.login_name, u.login_mail, u.password,"
        "    u.registration_name, u.registration_mail, u.registration_created_date, u.registration_created_by,"
        "    ud.api_name,"
        "    COALESCE(r.roles, '[]') AS roles,"
        "    COALESCE(s.acl, '[]') AS acl"
        "  FROM paged_users u"
        "  LEFT JOIN roles_agg r ON u.user_id = r.user_id"
        "  LEFT JOIN services_agg s ON u.user_id = s.user_id"
        f" LEFT JOIN {tables.User_Profile.__name__} ud ON u.user_id = ud.user_id"
    )
    return partial_query """
