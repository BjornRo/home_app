from typing import TypedDict

from litestar import get
from litestar.controller import Controller
from litestar.enums import MediaType
from litestar.response import File

from core.jwt_config import ACCESS_KEYDATA, REFRESH_KEYDATA
from guards.guards import root_or_local_guard


class PubKeyData(TypedDict):
    created: str
    pubkey: str
    signature: str


class JWTPubKeys(TypedDict):
    refresh: PubKeyData
    access: PubKeyData


class RootController(Controller):
    path = "/"
    tags = ["root"]

    @get(path="/", guards=[root_or_local_guard])
    async def index(self) -> dict[str, str]:
        return {"Hello": "world"}

    @get(path="/favicon.ico")
    async def favicon(self) -> File:
        return File("./static/favicon.ico")

    @get(path="/jwt_pubkeys", guards=[root_or_local_guard])
    async def jwt_pubkey(self) -> JWTPubKeys:
        """
        Returns the public keys in PEM format for the access and refresh tokens.
        Created-key as when the key was created.
        Signature is: created+pubkey -> sha384 -> sign with root_ca-key -> base64

        Validate: x509verify(ca=root_ca_cert, sign=b64decode(signature), data=created+pubkey, digest=sha384)
        """
        return JWTPubKeys(
            refresh=PubKeyData(
                created=REFRESH_KEYDATA.created.isoformat().replace("Z", "+00:00"),
                pubkey=REFRESH_KEYDATA.keys.public,
                signature=REFRESH_KEYDATA.public_key_sign,
            ),
            access=PubKeyData(
                created=ACCESS_KEYDATA.created.isoformat().replace("Z", "+00:00"),
                pubkey=ACCESS_KEYDATA.keys.public,
                signature=ACCESS_KEYDATA.public_key_sign,
            ),
        )

    @get("/robots.txt", media_type=MediaType.TEXT)
    async def robots(self) -> str:
        return "User-agent: *\nDisallow: /"
