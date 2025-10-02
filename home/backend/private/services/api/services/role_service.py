import msgspec
from core import enums
from storage.db.repositories.user_role_repository import UserRoleRepository


class RoleService(msgspec.Struct):
    repo_role: UserRoleRepository

    def get_all_roles(self):
        return list(enums.UserRoles)
