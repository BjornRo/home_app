import msgspec
from storage.db.repositories.user_meta_repository import UserMetaRepository


class MetaService(msgspec.Struct):
    repo_meta: UserMetaRepository

    async def number_of_users(self):
        return await self.repo_meta.number_of_users()

    async def online_users(self):
        return await self.repo_meta.online_users()