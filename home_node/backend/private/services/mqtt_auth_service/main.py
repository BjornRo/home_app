from os import environ
from typing import TypedDict

import orjson as json
import uvicorn
from quart import Quart, Response, request
from utils import InternalRolesEnum, SurrealDB

app = Quart(__name__, static_folder=None, template_folder=None)
db = SurrealDB(environ["DB_URI"], database="internal")


class UserAuth(TypedDict):
    clientid: str
    username: str
    password: str


ERR_RESP = Response(status=401)
OK_RESP = Response(status=204)


@app.route("/auth", defaults={"path": ""}, methods=["POST"])
@app.route("/auth/", defaults={"path": ""}, methods=["POST"])
@app.route("/auth/<path:path>", methods=["POST"])
async def auth(path: str):
    try:
        data: UserAuth | None = json.loads(await request.body)
        if data and data["password"] and data["username"] and data["clientid"]:
            if path:
                if len(path) > 30:
                    return ERR_RESP
                roles = InternalRolesEnum.convert(path.lower().split("/", maxsplit=3))
                if len(roles) >= 3:
                    return ERR_RESP
            else:
                roles = ()

            if await db.auth_user(name=data["username"], pwd=data["password"], filter_roles=roles):
                return OK_RESP
    except:
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
        ssl_keyfile="/certs/mqtt/mqtt_auth.key",
        ssl_certfile="/certs/mqtt/mqtt_auth.crt",
        ws="none",
    )
