from datetime import UTC, datetime, timedelta
from typing import TypedDict

from appdata import shared  # type: ignore
from litestar import Router, get, post
from litestar.controller import Controller
from litestar.exceptions import ClientException, HTTPException
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.status_codes import HTTP_410_GONE

from clients.mail import Mail
from core import exceptions, settings, types
from guards.guards import disabled_guard
from services.registration_service import RegistrationService
from utils import validation

from .login import LoginController
from .logout import LogoutController
from .token import TokenController

rate_limit = RateLimitConfig(rate_limit=("minute", 5), store="valkey_store")
token_expiry = timedelta(hours=12)


class TokenGone(HTTPException):
    status_code = HTTP_410_GONE
    detail = "Token expired, register again"


class UserRegistration(TypedDict):
    name: str
    pwd: str
    mail: str


class RegistrationController(Controller):
    tags = ["registration"]
    guards = [disabled_guard]

    @get(
        path="/confirm",
        status_code=204,
        raises=[TokenGone],
    )
    async def confirm_mail(self, registration_service: RegistrationService, token: str) -> None:
        if await registration_service.mail_confirm_user(token):
            return None
        raise TokenGone

    @post(
        path="/register",
        status_code=200,
        raises=[ClientException, types.AlreadyExists],
    )
    async def register_user(self, registration_service: RegistrationService, data: UserRegistration) -> str:
        try:
            validation.validate_password(data["pwd"])
        except Exception as e:
            raise ClientException(str(e))

        try:
            token = await registration_service.mail_store_confirmation(
                expiry_date=token_expiry,
                login_name=data["name"],
                login_mail=data["mail"],
                password=data["pwd"],
            )
            # TODO add link to confirm later.
            expire_date_str = shared.datetime_to_isofmtZ(datetime.now(UTC) + token_expiry, "minutes")
            with Mail().compose(to=data["mail"], subject=f"Confirm registration to {settings.HOSTNAME}") as msg:
                msg.attach_plain(token)
                msg.attach_plain(f"Expires at UTC: {expire_date_str}")
                await msg.send()
            return token
        except exceptions.IntegrityError:
            raise types.AlreadyExists("name or mail already exists")
        except exceptions.ValidationError:
            raise ClientException("invalid name or mail")


AuthRouter = Router(
    path="/auth",
    middleware=[rate_limit.middleware],
    route_handlers=[
        LoginController,
        LogoutController,
        TokenController,
        RegistrationController,
    ],
)
