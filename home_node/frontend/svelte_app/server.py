import time
from http.cookiejar import DefaultCookiePolicy

import uvicorn
from httpx import AsyncClient, Response
from quart import Quart, make_response, request
from quart_cors import cors

from build.cred import domain, host, uri_domain_port

# pip install -U httpx flask flask-cors

# domain = "*"
http = AsyncClient(base_url=host, timeout=10)
http._cookies.jar.set_policy(DefaultCookiePolicy(allowed_domains=[]))
app = Quart(__name__)
cors(app, allow_credentials=True, allow_origin=[uri_domain_port])

async def responer(res: Response):
    try:
        if res.content:
            data = res.json()
            if isinstance(data, int):
                data = str(data)
        else:
            data = '{"ok":204}'
        if res.status_code >= 300:
            return data, res.status_code
    except:
        print(res.content)
        data = {"msg": str(res.content)}

    resp = await make_response(data)
    for cookie in res.cookies.jar:
        new_cookie = dict(
            key=cookie.name,
            value=cookie.value or "",
            expires=cookie.expires,
            domain=domain,
            path=cookie.path,
            secure=False,
            httponly=True,
            samesite="lax",
        )
        resp.set_cookie(**new_cookie)  # type:ignore
    # resp.headers["Access-Control-Allow-Origin"] = "http://bjdev.duckdns.org:3000"
    # resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp, 200


def cookie_head():
    headers: dict[str, str] = {}
    if val := request.headers.get("Authorization"):
        headers["Authorization"] = val
    cookies: dict[str, str] = {}
    if tok := request.cookies.get("refresh_token"):
        cookies["refresh_token"] = tok
    if tok := request.cookies.get("access_token"):
        cookies["access_token"] = tok
    return cookies, headers


@app.route("/", defaults={"path": ""}, methods=["put"])
@app.route("/<path:path>", methods=["put"])
async def put(path: str):
    cookies, headers = cookie_head()
    res = await http.put(request.full_path, json=await request.get_json(True, True), headers=headers, cookies=cookies)
    return await responer(res)


@app.route("/", defaults={"path": ""}, methods=["PATCH"])
@app.route("/<path:path>", methods=["PATCH"])
async def patch(path: str):
    cookies, headers = cookie_head()
    res = await http.patch(request.full_path, json=await request.get_json(True, True), headers=headers, cookies=cookies)
    return await responer(res)


@app.route("/", defaults={"path": ""}, methods=["DELETE"])
@app.route("/<path:path>", methods=["DELETE"])
async def delete(path: str):
    cookies, headers = cookie_head()
    res = await http.delete(request.full_path, headers=headers, cookies=cookies)
    return await responer(res)


@app.route("/", defaults={"path": ""}, methods=["POST"])
@app.route("/<path:path>", methods=["POST"])
async def post(path: str):
    cookies, headers = cookie_head()
    res = await http.post(request.full_path, json=await request.get_json(True, True), headers=headers, cookies=cookies)
    return await responer(res)


@app.route("/", defaults={"path": ""}, methods=["GET"])
@app.route("/<path:path>", methods=["GET"])
async def get(path: str):
    if "favicon" in path:
        return "", 404
    cookies, headers = cookie_head()
    res = await http.get(request.full_path, headers=headers, cookies=cookies)
    x = await responer(res)
    return x


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8888,
        log_level="warning",
        reload=True,
    )
