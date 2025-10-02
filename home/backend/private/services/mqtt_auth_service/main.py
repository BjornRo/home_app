__import__("sys").path.append("/")
from os import environ

import msgspec
import uvicorn
from quart import Quart, Response, request
from utils import SQLDB

from appdata.internal_shared import InternalRolesEnum

app = Quart(__name__, static_folder=None, template_folder=None)
db = SQLDB(environ["DATA_PATH"] + environ["DB_INTERNAL"])


class UserAuth(msgspec.Struct):
    clientid: str
    username: str
    password: str


json_decoder = msgspec.json.Decoder(UserAuth).decode

ERR_RESP = Response(status=401)
OK_RESP = Response(status=204)


@app.route("/auth", defaults={"path": ""}, methods=["POST"])
@app.route("/auth/", defaults={"path": ""}, methods=["POST"])
@app.route("/auth/<path:path>", methods=["POST"])
async def auth(path: str):
    try:
        data = json_decoder(await request.body)
        if path:
            if len(path) > 30:
                return ERR_RESP
            roles = InternalRolesEnum.convert(path.lower().split("/", maxsplit=3))
            if len(roles) >= 3:
                return ERR_RESP
        else:
            roles = ()

        if await db.auth_user(name=data.username, pwd=data.password, filter_roles=roles):
            return OK_RESP
    except Exception as e:
        pass

    return ERR_RESP


@app.route("/acl", methods=["POST"])
@app.route("/acl/", methods=["POST"])
async def acl():
    return OK_RESP


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8888,
        log_level="critical",
        workers=1,
        ssl_ca_certs="/certs/ca/root.crt",
        ssl_keyfile="/certs/mqtt/mqtt_auth_service.key",
        ssl_certfile="/certs/mqtt/mqtt_auth_service.crt",
        ws="none",
    )
