from typing import TypedDict

from litestar import get, post
from litestar.config.response_cache import CACHE_FOREVER
from litestar.controller import Controller

from utils import validation


class Password(TypedDict):
    password: str


class TestValidationController(Controller):
    path = "/test_validation"
    tags = ["test_validation"]

    @get(path="/name/{name:str}", cache=CACHE_FOREVER)
    async def test_name(self, name: str) -> bool:
        try:
            validation.validate_name(name)
            return True
        except:
            return False

    @get(path="/mail/{mail:str}", cache=CACHE_FOREVER)
    async def test_mail(self, mail: str) -> bool:
        try:
            validation.validate_mail(mail)
            return True
        except:
            return False

    @post(path="/password")
    async def test_password(self, data: Password) -> bool:
        try:
            validation.validate_password(data["password"])
            return True
        except:
            return False
