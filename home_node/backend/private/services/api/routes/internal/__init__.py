from litestar import Router

from .acl import InternalACLController
from .auth import InternalAuthController
from .cache_ws import InternalCacheController
from .mqtt import InternalMqttAuthController
from .root import InternalRootController
from .service import InternalServiceController
from .user import InternalUserController

InternalServiceRouter = Router(
    path="/internal",
    route_handlers=[
        InternalACLController,
        InternalAuthController,
        InternalCacheController,
        InternalMqttAuthController,
        InternalRootController,
        InternalServiceController,
        InternalUserController,
    ],
)
