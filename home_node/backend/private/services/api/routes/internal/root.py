from typing import cast

import db.internal.queries as internal_queries
from db.internal.models import (
    InternalRolesEnum,
    InternalUserAPIRegistration,
    InternalUserUpdate,
)
from db.strategy.surreal import TableInternal
from litestar import delete, get, patch, post
from litestar.connection import Request
from litestar.controller import Controller
from litestar.exceptions import (
    ClientException,
    NotFoundException,
    PermissionDeniedException,
)
from modules.guards import root_guard
from modules.myjwt import JWTToken, jwt_middleware
from utils import hash_password_b64


class InternalRootController(Controller):
    path = "/"
    tags = ["internal_root"]
    middleware = [jwt_middleware]
    guards = [root_guard]

    @get(path="/", status_code=200)
    async def root(self) -> str:
        return "internal_root"
