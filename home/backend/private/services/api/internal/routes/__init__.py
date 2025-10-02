from core.constants import SECURITY_TAG
from guards.guards import root_guard
from internal import internal_dependencies
from internal.internal_utils import api_guard
from internal.middlewares import JWTInternalAuthMiddleware
from litestar import Router, get
from litestar.controller import Controller
from litestar.di import Provide
from litestar.middleware.rate_limit import RateLimitConfig
from middleware.middlewares import JWTAuthenticationMiddleware

from .admin import AdminController
from .auth import InternalAuthController
from .balcony import BalconyController
from .mqtt import InternalMqttAuthController
from .service import InternalServiceController

rate_limit = RateLimitConfig(rate_limit=("minute", 3), store="valkey_store")
rate_limit_relaxed = RateLimitConfig(rate_limit=("minute", 6), store="valkey_store")


class InternalRootController(Controller):
    path = "/"
    tags = ["internal_root"]

    @get(path="/", status_code=200)
    async def root(self) -> str:
        return "internal_root"


__InternalProtectedRouter = Router(
    path="/",
    middleware=[JWTInternalAuthMiddleware, rate_limit.middleware],
    guards=[api_guard],
    security=[SECURITY_TAG.access_token],
    route_handlers=[
        InternalMqttAuthController,
        InternalServiceController,
    ],
)


__InternalAdminRouter = Router(
    path="/",
    middleware=[JWTAuthenticationMiddleware, rate_limit_relaxed.middleware],
    guards=[root_guard],
    security=[SECURITY_TAG.access_token],
    route_handlers=[
        InternalRootController,
        AdminController,
    ],
)

InternalRouter = Router(
    path="/internal",
    dependencies={
        "internal_mqtt_service": Provide(internal_dependencies.provide_internal_mqtt_service),
        "internal_user_service": Provide(internal_dependencies.provide_internal_user_service),
        "internal_token_service": Provide(internal_dependencies.provide_internal_token_service),
    },
    route_handlers=[
        InternalAuthController,
        __InternalAdminRouter,
        __InternalProtectedRouter,
        BalconyController,
    ],
)
