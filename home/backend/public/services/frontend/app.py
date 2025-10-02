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
    data = loads((await http.get("data/sensors")).content)
    try:
        refdict = data["home"]["kitchen"]
        data["home"]["kitchen"] = refdict["0"]

        refdict = data["home"]["balcony"].pop("0")
        data["home"]["balcony"]["inside"] = refdict

        refdict = data["home"]["balcony"].pop("1")
        data["home"]["balcony"]["outside"] = refdict

        resp = await make_response(dumps(data, indent=2))
        resp.headers["Content-Type"] = "application/json"
        return resp
    except:
        return await make_response(None)
