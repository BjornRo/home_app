import db.distlock as dl
import db.internal.queries as internal_queries
import db.queries as queries
from constants import HOSTNAME, MAIL_SETTINGS
from litestar import Litestar, get
from litestar.openapi import OpenAPIConfig, OpenAPIController
from litestar.openapi.spec import Components, SecurityScheme
from litestar.response import Redirect
from litestar.status_codes import (
    HTTP_301_MOVED_PERMANENTLY,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from modules.guards import root_or_local_jwt_guard
from routes.auth import AuthedController
from routes.data import DataController
from routes.internal import InternalServiceRouter
from routes.misc import MiscController
from routes.register import RegisterController
from routes.root import RootController
from routes.user import UserController
from utils import Mail, db_schema_init_api, db_schema_init_internal, http_401_resp

"""
The following models are used in the API.

USER = U
SERVICE = S

Login flow:
    U sends login -> login service verifies U -> Returns tokens to U
    U request a resource from S -> S uses queries.get_app_user(jwt.claim.sub) verifies U -> Returns resource
    S should:
        in an event where user access to a service is modified, delete the cache for the served user

This is general app model to make it run.
"""


async def startup() -> None:
    await dl.init_all()
    Mail().config(
        **MAIL_SETTINGS,
        hostname=HOSTNAME,
    )
    for i in db_schema_init_internal:
        await internal_queries.query(i)
    db_schema_init_internal.clear()

    for i in db_schema_init_api:
        await queries.query(i)
    db_schema_init_api.clear()


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
        HTTP_404_NOT_FOUND: http_401_resp,
        HTTP_405_METHOD_NOT_ALLOWED: http_401_resp,
    },
    route_handlers=[
        redirect_schema,
        AuthedController,
        DataController,
        RegisterController,
        RootController,
        UserController,
        MiscController,
        InternalServiceRouter,
    ],
    on_startup=[startup],
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
