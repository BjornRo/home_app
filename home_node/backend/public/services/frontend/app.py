from json import dumps
from os import environ
from tomllib import load

import httpx
from orjson import loads
from quart import Quart, make_response

with open(environ["DATA_PATH"] + "default.toml", "rb") as f:
    api = load(f)["api"]

ROOT_CA = "/certs/ca/root.crt"

app = Quart(__name__)
http = httpx.AsyncClient(base_url=f"https://{api}:{environ["APIPORT"]}/", verify=ROOT_CA)


@app.route("/")
async def index():
    # Convert to a nicer format, use data/sensors instead for faster response
    resp = await make_response(dumps(loads((await http.get("data/sensors")).content), indent=2))
    resp.headers["Content-Type"] = "application/json"
    return resp
