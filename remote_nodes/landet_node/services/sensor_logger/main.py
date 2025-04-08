import asyncio
from datetime import UTC, datetime, timedelta
from glob import glob
from json import dumps as _json_dumps
from os import environ, path
from typing import NoReturn

import ujson as json
import utils
import uvloop  # type: ignore
from aiocron import crontab
from aiosqlite import connect

CRON_AT_TIME = 30
CRON_JOB = f"*/{CRON_AT_TIME} * * * *"  # Every 30 minutes

# DB
DB_FILEPATH = environ["DATA_PATH"] + "sensordata.sqlite"
db_connect = lambda: connect(DB_FILEPATH)

# File to read temperature from
TEMPERATURE_FILE = glob("/sys/bus/w1/devices/28*")[0] + "/w1_slave"

tmp_data: dict[str, utils.TmpData] = {}

loop: asyncio.AbstractEventLoop = uvloop.new_event_loop()
asyncio.set_event_loop(loop)


async def main():
    # Check db or create
    if not path.isfile(DB_FILEPATH):
        async with db_connect() as db:
            await db.execute("CREATE TABLE snapshots (datetime DATETIME PRIMARY KEY, value TEXT NOT NULL)")
            await db.commit()

    await asyncio.gather(
        utils.MQTTHandler(tmp_data).run(),
        http_requests(),
    )


async def http_requests() -> NoReturn:
    class Shielded:
        def __init__(self, func):
            self.func = func

        async def __call__(self, *args, **kw):
            utils.fire_forget_coro(self.func(*args, **kw))

    @Shielded
    async def client_handler_cb(_: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            jsdata = _json_dumps(tmp_data, default=str, indent=2).encode()
            writer.write(b"HTTP/1.1 200 OK\r\n")
            writer.write(b"Connection: close\r\nContent-Type: application/json\r\nContent-Length: ")
            writer.write(str(len(jsdata)).encode())
            writer.write(b"\r\n\r\n")
            writer.write(jsdata)
            await writer.drain()
        except:
            pass
        writer.close()
        await writer.wait_closed()

    async with await asyncio.start_server(client_handler_cb, "", 80) as s:
        await s.serve_forever()


@crontab(CRON_JOB, start=True, loop=loop)
async def insert_db_task():
    try:
        now_time = datetime.now(UTC)
        new_data: list[dict] = []
        for device_name, data_dict in tmp_data.items():
            if data_dict["date"] > (now_time - timedelta(minutes=CRON_AT_TIME)):
                new_data.append(dict(name=device_name) | data_dict["data"])
        async with db_connect() as db:
            await db.execute(
                "INSERT INTO snapshots VALUES (?, ?)",
                (now_time.isoformat().replace("+00:00", "Z"), json.dumps(new_data)),
            )
            await db.commit()
    except:
        pass


if __name__ == "__main__":
    asyncio.run(main())
