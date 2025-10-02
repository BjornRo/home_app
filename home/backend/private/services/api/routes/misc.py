from core.constants import SECURITY_TAG
from guards.guards import root_guard, root_or_local_guard, root_or_local_jwt_guard
from litestar import get
from litestar.controller import Controller
from services.meta_service import MetaService


class MiscController(Controller):
    path = "/misc"
    tags = ["misc"]
    # middleware = [jwt_middleware]
    guards = [root_or_local_jwt_guard]
    security = [SECURITY_TAG.access_token]

    @get(path="/total_users", cache=60)
    async def total_users(self, meta_service: MetaService) -> int:
        return await meta_service.number_of_users()

    @get(path="/online_users", cache=20)
    async def online_users(self, meta_service: MetaService) -> int:
        return await meta_service.online_users()
