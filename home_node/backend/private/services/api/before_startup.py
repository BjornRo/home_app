from __future__ import annotations

import os

if secret_filepath := "secrets":  # Generate temp secrets.
    import time
    from datetime import UTC, datetime, timedelta
    from hashlib import sha256

    if os.path.exists(secret_filepath):
        with open(secret_filepath, "rt") as f:
            date = datetime.fromisoformat(f.readline().strip()) + timedelta(days=90)
        if date <= datetime.now(UTC):
            os.remove(secret_filepath)
    if not os.path.exists(secret_filepath):
        with open(secret_filepath, "wt") as f:
            f.write(datetime.now(UTC).isoformat().replace("+00:00", "") + "Z\n")
            for _ in range(8):
                time.sleep(0.05)
                secret = str(list(sha256(os.urandom(40) + time.time_ns().to_bytes(8)).digest())).replace(" ", "")[1:-1]
                f.write(secret + "\n")

# Lazy load, to speed up startup time. File exists -> Ftp -> Create db
import asyncio
import zipfile
from sys import exit, path

import asyncssh

path.append("/")  # To import schema.
from constants import DATA_PATH, DB_FILE
from db.models import TableAPI

from appdata.cfg_schema import FileData

NAMESPACE = "app"
DATABASE = "api"
INTERNAL_DATABASE = "internal"

if os.path.exists(DATA_PATH + DB_FILE):
    time.sleep(10)
    import json
    import urllib.request as r

    addr = os.environ["DB_URI"].split("://")[1].split("/")[0]
    rq = r.Request(f"http://{addr}/key/{TableAPI.USER_ROLE}")
    rq.add_header("NS", NAMESPACE)
    rq.add_header("DB", DATABASE)
    rq.add_header("Accept", "application/json")
    if json.loads(r.urlopen(rq).read())[-1]["result"]:
        exit(0)  # If atleast one result exist.

""" FTP """
import shutil
from ftplib import FTP, FTP_TLS, error_perm
from pathlib import Path
from tomllib import load as toml_load
from typing import cast

with open(DATA_PATH + "default.toml", "rb") as f:
    CFG = cast(FileData, toml_load(f))


class SingleFileBackupFTP_TLS(FTP_TLS):
    __slots__ = ("user", "passwd", "workfolder", "target_file", "backup_size")

    def __init__(
        self, host: str, port: int, user: str, passwd: str, workdir: str, filepath: str, ftp_folder: str, size=10
    ):
        super().__init__()  # Has to be first, otherwise it connects due to self.host
        self.port, self.host, self.user, self.passwd = port, host, user, passwd
        # e.g. mydir, leading/trailing slash optional
        self.workfolder = Path(workdir.strip("/").lower()) / Path(ftp_folder.strip("/").lower())
        self.target_file = Path(filepath.rstrip("/"))
        self.backup_size = size  # Generates new backups and deletes older that exceeds this number.

    def __enter__(self):
        self.connect()
        self.login(user=self.user, passwd=self.passwd, secure=True)
        self.prot_p()  # Get the "lowest" drive and create full path. Change to it
        self.cwd(sorted(self.nlst())[0])
        for path in ("backup" / self.workfolder).as_posix().split("/"):
            try:
                self.mkd(path)  # Throws error if path exists
            except error_perm:
                pass
            self.cwd(path)
        self.cwd("..")  # go back one step
        return self

    def get_file(self, overwite=True) -> bool:
        if self.target_file.name in self.lsdir():
            if overwite and os.path.exists(self.target_file):
                shutil.rmtree(self.target_file.parent, ignore_errors=True)
            os.makedirs(self.target_file.parent, exist_ok=True)
            with open(self.target_file, "wb") as f:
                try:
                    self.retrbinary(f"RETR {self.target_file.name}", f.write)
                    return True
                except:
                    pass
        return False

    def lsdir(self, dir: str = "", sorted_oldest_first=False) -> list[str]:
        xs = []
        self.dir("-t" * sorted_oldest_first, dir, lambda x: xs.append(x[x.rindex(" ") + 1 :]))
        return xs

    def ntransfercmd(self, cmd, rest=None):
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        return (  # Transfers need the same session as the control connection. FTP_TLS does not do this.
            self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session),  # type: ignore
            size,
        )


filepath = Path(f"{DATA_PATH}tmp/dbbk/{DB_FILE}.zip")
res = False
with SingleFileBackupFTP_TLS(**CFG["ftp"], filepath=filepath.as_posix()) as ftp:
    res = ftp.get_file()
if res:
    with zipfile.ZipFile(filepath, "r") as zip:
        db_names = zip.namelist()
        zip.extractall(filepath.parent)

    async def call_ssh():
        ssh_cfg = {
            "host": "host.docker.internal",
            "port": CFG["ssh"]["port"],
            "known_hosts": None,
            "username": CFG["ssh"]["user"],
            "client_keys": ["/certs/sensor_listener/sshkey"],
        }

        async with asyncssh.connect(**ssh_cfg) as ssh:
            for db in db_names:
                _c = f"docker exec -it graph /surreal import --conn http://127.0.0.1:8000 --ns app --db {db} {filepath.parent}/{db}"
                if result := (await ssh.run(_c)).exit_status:
                    print(f"Program exited with status {result}")
                    return False
        return True

    result = asyncio.run(call_ssh())
    shutil.rmtree(filepath.parent, ignore_errors=True)
    if result:
        exit(0)

"""
Last step
Create DB since it clearly does not exist

"""

import time
from datetime import UTC, datetime, timedelta
from typing import cast

from constants import DB_URI
from db.internal.models import InternalRolesEnum
from db.models import UserRolesEnum
from db.strategy.surreal import SurrealDB, SurrealInternalDB, TableAPI
from utils import hash_password_b64

SCHEMA_API = "db/strategy/surreal/schema.srql"
SCHEMA_INTERNAL_API = "db/strategy/surreal/internal_schema.srql"


asyncio.set_event_loop(asyncio.new_event_loop())


async def create_db():
    """Internal API"""
    internal_db = SurrealInternalDB(DB_URI, database=INTERNAL_DATABASE)
    with open(SCHEMA_INTERNAL_API, "rt") as f:
        await internal_db.query(f.read())

    for user in CFG["api"]["internal_users"]:
        user_id = await internal_db.insert_internal_user(
            name=user["name"],
            hash_b64_pwd=await hash_password_b64(user["password"]),
            created_by_user_id="root",
            enabled=True,
        )
        assert user_id
        for role in user["roles"]:
            _role = InternalRolesEnum(role)
            await internal_db.insert_internal_userrole(
                name_or_user_id=user_id,
                role=_role,
                given_by_user_id="root",
            )

    """API"""
    api_db = SurrealDB(DB_URI, database=DATABASE)
    with open(SCHEMA_API, "rt") as f:
        await api_db.query(f.read())
    for r in UserRolesEnum:
        await api_db.query(f"CREATE ONLY {TableAPI.USER_ROLE}:{r}")

    for user in CFG["api"]["users"]:
        user_id = await api_db.insert_user(
            name=user["name"],
            mail=None,
            hash_b64_pwd=await hash_password_b64(user["password"]),
            created_by_user_id="root",
            role=UserRolesEnum(user["roles"].pop()),
        )
        assert user_id
        for role in user["roles"]:
            _role = UserRolesEnum(role)
            await api_db.insert_userrole(
                user_id=user_id,
                role=_role,
                end_date=None,
                given_by_user_id="root",
            )

    exit(0)


asyncio.run(create_db())
