import asyncio

import ujson as json
import utils as ut
import uvloop  # type: ignore

loop: asyncio.AbstractEventLoop = uvloop.new_event_loop()
asyncio.set_event_loop(loop)

ERR_RESP = b"HTTP/1.1 401 Unauthorized\r\n\r\n"
OK_RESP = b"HTTP/1.1 201 OK\r\n\r\n"

api_client = ut.APIClient(**ut.load_config())


async def main():
    await ut.if_not_exist_create_db()
    if not await api_client.init():
        async with ut.db_connect() as db:
            async with db.execute("SELECT * FROM User") as cursor:
                if await cursor.fetchone() is None:
                    raise RuntimeError("No user in db and api login failed")
    await http_server()


async def http_server():
    async def client_handler_cb(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await handle_client_request(reader, writer)
        writer.close()
        await writer.wait_closed()

    async with await asyncio.start_server(client_handler_cb, "", 80) as s:
        await s.serve_forever()


async def handle_acl(data: ut.UserAcl):
    if resp := await api_client.post("mqtt/acl_jwt", data):
        if b"true" in resp.content:
            ut.fire_forget_coro(ut.insert_acl(data))
            return True
    elif (acl := await ut.get_acl(data)) and acl["acc"] == data["acc"]:
        return True
    return False


async def handle_auth(data: ut.UserAuth):
    if len(data["password"]) >= 4:
        if resp := await api_client.post("mqtt/auth_jwt/remote/local", data):
            if b"true" in resp.content:
                ut.fire_forget_coro(ut.insert_user(data))
                return True
        elif (pwd := await ut.get_user_password(data["username"])) and ut.check_pwd(data["password"], pwd):
            return True
    return False


async def handle_client_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    response = ERR_RESP
    try:
        content_length = 0
        is_acl = (await reader.readline()).split(b"/")[1][:3] == b"acl"
        data = await reader.readline()
        while data != b"\r\n":
            if not data:
                return
            if not (content_length or ((data[0] - 67) % 32 or (data[8] - 76) % 32)):
                content_length = int(data[data.find(b":") + 1 :])  # int handles \r\n, space
            data = await reader.readline()
        req = json.loads(await reader.readexactly(content_length))
        if len(req["username"]) >= 4 and len(req["clientid"]) >= 4:
            if await (handle_acl(req) if is_acl else handle_auth(req)):
                response = OK_RESP
    except RuntimeError:
        __import__("traceback").print_exc()
    except:
        pass
    writer.write(response)
    await writer.drain()


if __name__ == "__main__":
    asyncio.run(main())
