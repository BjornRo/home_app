__import__("sys").path.append("/")
import asyncio

import clients.mail
import dependencies
from core import settings
from guards.guards import root_or_local_jwt_guard
from internal import internal_dependencies
from internal.routes import InternalRouter
from litestar import Litestar, get
from litestar.config.response_cache import ResponseCacheConfig
from litestar.di import Provide
from litestar.openapi import OpenAPIConfig, OpenAPIController
from litestar.openapi.spec import Components, SecurityScheme
from litestar.response import Redirect
from litestar.status_codes import (
    HTTP_301_MOVED_PERMANENTLY,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from litestar.stores.valkey import ValkeyStore
from routes import auth
from routes.acl import AclController
from routes.data import DataController
from routes.misc import MiscController
from routes.root import RootController
from routes.test_validation import TestValidationController
from routes.users import UserController
from utils import helpers, http_helpers


async def startup(app: Litestar) -> None:
    app.state.internal_token_service = await internal_dependencies.provide_internal_token_service()
    app.state.token_service = await dependencies.provide_token_service()
    clients.mail.Mail().config(
        **settings.MAIL_SETTINGS,
        hostname=settings.HOSTNAME,
    )
    await asyncio.gather(
        dependencies.start(app),
        internal_dependencies.start(app),
    )


async def shutdown(app: Litestar) -> None:
    helpers.process_pool.shutdown(wait=True)
    await asyncio.gather(
        dependencies.close(),
        internal_dependencies.close(),
    )


class MyOpenAPIController(OpenAPIController):
    path = "/rschema"
    guards = [root_or_local_jwt_guard]


@get(
    path="/schema",
    guards=[root_or_local_jwt_guard],
    status_code=HTTP_301_MOVED_PERMANENTLY,
    include_in_schema=False,
)
async def redirect_schema() -> Redirect:
    """Redoc is default, no 2nd path. Other: swagger, elements, rapidoc"""
    return Redirect(path="/rschema/elements", status_code=HTTP_301_MOVED_PERMANENTLY)


app = Litestar(
    exception_handlers={
        HTTP_404_NOT_FOUND: http_helpers.http_401_resp,
        HTTP_405_METHOD_NOT_ALLOWED: http_helpers.http_401_resp,
    },
    route_handlers=[
        redirect_schema,
        auth.AuthRouter,
        AclController,
        DataController,
        RootController,
        UserController,
        MiscController,
        TestValidationController,
        InternalRouter,
    ],
    stores={"valkey_store": ValkeyStore(valkey=dependencies.get_api_cache_client())},
    response_cache_config=ResponseCacheConfig(store="valkey_store"),
    dependencies={
        "acl_service": Provide(dependencies.provide_acl_service),
        "auth_service": Provide(dependencies.provide_auth_service),
        "ban_service": Provide(dependencies.provide_ban_service),
        "meta_service": Provide(dependencies.provide_meta_service),
        "registration_service": Provide(dependencies.provide_registration_service),
        "role_service": Provide(dependencies.provide_role_service),
        "token_service": Provide(dependencies.provide_token_service),
        "user_service": Provide(dependencies.provide_user_service),
        # Caches
        "data_cache": Provide(dependencies.provide_data_cache),
    },
    on_startup=[startup],
    on_shutdown=[shutdown],
    openapi_config=OpenAPIConfig(
        title="My API",
        version="0.0.1",
        openapi_controller=MyOpenAPIController,
        components=Components(
            security_schemes={
                "RefreshToken": SecurityScheme(
                    type="apiKey",
                    name="refresh_token",
                    security_scheme_in="cookie",
                ),
                "AccessToken": SecurityScheme(
                    type="apiKey",
                    name="access_token",
                    security_scheme_in="cookie",
                ),
                "BearerToken": SecurityScheme(
                    type="http",
                    scheme="bearer",
                ),
            },
        ),
    ),
    # debug=True,
)
