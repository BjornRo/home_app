import db.distlock as dl
import db.queries as queries
from constants import DEFAULT_SECURITY_TAG as SECTAG
from litestar import get
from litestar.controller import Controller
from modules.guards import root_guard, root_or_local_guard, root_or_local_jwt_guard
from modules.myjwt import jwt_middleware


class MiscController(Controller):
    path = "/misc"
    tags = ["misc"]
    # middleware = [jwt_middleware]
    guards = [root_or_local_jwt_guard]
    security = SECTAG

    @get(path="/online_users")
    async def online_users(self) -> int:
        return await dl.online_users.size()

    @get(path="/total_users", cache=60)
    async def total_users(self) -> int:
        return await queries.number_of_users()
