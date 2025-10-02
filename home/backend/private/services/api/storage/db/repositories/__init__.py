import aiosqlite
from appdata import shared  # type: ignore

from core import exceptions, types
from storage.db.sql.sqlite import SQLite
from utils import helpers


async def update_fields(db: SQLite, table: str, user_id: types.UserID, **fields):
    if not fields:
        raise exceptions.UserInputError("No fields given")

    time_now = shared.datetime_now_isofmtZ()

    _fields = ",".join(f"{col} = :{col}" for col in fields.keys())
    _diff_clause = " OR ".join(f"{col} IS NOT :{col}" for col in fields.keys())
    query = (
        f"UPDATE {table} SET {_fields}, last_updated_date = '{time_now}'"
        f"  WHERE user_id = :user_id AND ({_diff_clause})"
    )

    try:
        await db.execute_void(query, dict(**fields, user_id=user_id))
    except aiosqlite.IntegrityError as e:
        raise exceptions.IntegrityError(str(e)) from e
    except Exception as e:
        shared.print_err(e)
        raise
