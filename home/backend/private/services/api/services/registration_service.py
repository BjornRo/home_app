import secrets

import msgspec
from core import types
from services.user_service import UserService
from storage.db.repositories.user_meta_repository import UserMetaRepository


class RegistrationService(msgspec.Struct):
    user_service: UserService
    repo_meta: UserMetaRepository

    async def mail_store_confirmation(
        self,
        expiry_date: types.DateT,
        login_name: str,
        login_mail: str,
        password: str,
    ):
        """
        Raises:
            ValidationError: if value(s) given are invalid
            IntegrityError: if value already exists
        """
        user_id = await self.user_service.create_user(
            login_name=login_name,
            login_mail=login_mail,
            password=password,
            enable=False,
            created_by=None,
        )
        token = secrets.token_urlsafe(24)
        await self.repo_meta.mail_store_confirmation(user_id, token=token, expiry_date=expiry_date)
        return token

    async def mail_confirm_user(self, token: str):
        return await self.repo_meta.mail_confirm_user(token)
