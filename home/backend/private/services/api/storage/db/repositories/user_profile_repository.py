from typing import TypedDict, Unpack

import msgspec
from core import exceptions, types
from storage.db import tables
from storage.db.sql.sqlite import SQLite

from . import update_fields


class UserProfileUpdateFields(TypedDict, total=False):
    display_name: str


class UserProfileRepository(msgspec.Struct):
    db: SQLite

    async def get_user_profile(self, user_id: types.UserID):
        """
        Raises:
            NotFoundError: if name or mail does not exist
        """
        query = f"SELECT * FROM {tables.User_Profile.__name__} WHERE user_id = ?"
        if row := await self.db.fetch_one(query, (user_id,)):
            return msgspec.convert(row, type=tables.User_Profile)
        raise exceptions.NotFoundError

    async def update_user_profile(self, user_id: types.UserID, **fields: Unpack[UserProfileUpdateFields]):
        """
        Raises:
            UserInputError: if no fields are supplied
            IntegrityError: if value already exists
        """
        await update_fields(db=self.db, table=tables.User_Profile.__name__, user_id=user_id, **fields)
