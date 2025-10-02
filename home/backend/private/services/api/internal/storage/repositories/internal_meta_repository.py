import msgspec
from internal.storage import internal_tables
from storage.db.sql.sqlite import SQLite
from utils import time_helpers

from appdata import shared  # type:ignore


class InternalMetaRepository(msgspec.Struct, gc=False):
    db: SQLite

    # region: Token

    async def get_token_policy_unixtime(self, username: str) -> int:
        query = f"SELECT tokens_valid_after AS date FROM {internal_tables.User_Token_Policy.__name__} WHERE user_id = ?"
        return row["date"] if (row := await self.db.fetch_one(query, (username,))) else 0

    async def upsert_tokens_valid_after(self, username: str):
        query = (
            f"INSERT INTO {internal_tables.User_Token_Policy.__name__}"
            " (user_id, tokens_valid_after)"
            " VALUES (?, ?)"
            " ON CONFLICT(user_id) DO UPDATE SET tokens_valid_after = EXCLUDED.tokens_valid_after"
        )

        try:
            await self.db.execute_void(query, (username, time_helpers.unixtime()))
        except Exception as e:
            shared.print_err(e)
            raise

    # endregion
