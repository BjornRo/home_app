__import__("sys").path.append("./services/api")  # Import this context, otherwise imports fail
import asyncio
import os
import sqlite3
import sys
from contextlib import suppress
from multiprocessing import Process

import yaml

from appdata import cfg_schema
from services.api.utils import helpers

""" FLAG """
DELETE_EXISTING_DBS = False


with open("docker-compose.yml") as f:
    DOCKER_COMPOSE_ENV: dict[str, str] = yaml.safe_load(f)["x-db-path"]

APP_PATH = "./" + DOCKER_COMPOSE_ENV["DATA_PATH"].removeprefix("/")
CONFIG = cfg_schema.load_file(APP_PATH + cfg_schema.FILENAME)


def run():
    tasks = [
        (internal, APP_PATH + DOCKER_COMPOSE_ENV["DB_INTERNAL"]),
        (app, APP_PATH + DOCKER_COMPOSE_ENV["DB_APP"]),
        (data, APP_PATH + DOCKER_COMPOSE_ENV["DB_DATA"]),
    ]

    procs = []
    for func, dbfilepath in tasks:
        if DELETE_EXISTING_DBS:
            with suppress(FileNotFoundError):
                os.remove(dbfilepath)

        if not os.path.isfile(dbfilepath):
            p = Process(target=func, args=(dbfilepath,))
            p.start()
            procs.append(p)

    for p in procs:
        p.join()


def internal(dbfilepath: str):
    SCHEMA = """
    CREATE TABLE user (
        user_id TEXT PRIMARY KEY NOT NULL COLLATE NOCASE, -- AKA "login_name"
        pwd     TEXT NOT NULL,
        enabled BOOLEAN NOT NULL
    );

    CREATE TABLE user_registration (
        user_id      TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
        created_date DATETIME NOT NULL,
        FOREIGN KEY(user_id) REFERENCES user(user_id)
            ON UPDATE CASCADE
            ON DELETE CASCADE
    );

    CREATE TABLE role (
        name TEXT PRIMARY KEY NOT NULL COLLATE NOCASE
    );

    CREATE TABLE has_role (
        user_id      TEXT NOT NULL COLLATE NOCASE,
        role_name    TEXT NOT NULL COLLATE NOCASE,
        created_date DATETIME NOT NULL,
        FOREIGN KEY(user_id) REFERENCES user(user_id)
            ON UPDATE CASCADE
            ON DELETE CASCADE,
        FOREIGN KEY(role_name) REFERENCES role(name)
            ON UPDATE CASCADE
            ON DELETE CASCADE,
        PRIMARY KEY(user_id, role_name)
    );

    CREATE INDEX idx_has_role_user_id ON has_role(user_id);
    CREATE INDEX idx_has_role_role ON has_role(role_name);

    CREATE TABLE user_token_policy (
        user_id            TEXT PRIMARY KEY NOT NULL COLLATE NOCASE REFERENCES user(user_id)
            ON DELETE CASCADE,
        tokens_valid_after UNIXTIME NOT NULL
    );

    CREATE TABLE service_ownership (
        service_name TEXT NOT NULL COLLATE NOCASE PRIMARY KEY, -- logical link to app-database.
        user_id TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES user(user_id)
            ON DELETE CASCADE
    );
    CREATE INDEX idx_service_ownership_user_id ON service_ownership(user_id);
    """

    from appdata import internal_shared
    from services.api.internal.storage.repositories.internal_user_repository import (
        InternalUserRepository,
    )
    from services.api.internal.storage.sqlite_basic import INTERNALSQLite

    internal_repository = InternalUserRepository(db=INTERNALSQLite(dbfilepath))

    with sqlite3.connect(dbfilepath) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO role (name) VALUES (?)",
            [(r,) for r in internal_shared.InternalRolesEnum],
        )
        conn.commit()

    async def insert_async():
        tasks = []
        for user in CONFIG["api"]["internal_users"]:

            async def insert(user: cfg_schema.FileKeyAPI_User):
                await internal_repository.create_user(username=user["name"], pwd=user["password"], enabled=True)
                for role in user["roles"]:
                    await internal_repository.insert_role(
                        username=user["name"],
                        role=internal_shared.InternalRolesEnum(role),
                    )

            tasks.append(insert(user))
        await asyncio.gather(*tasks)

    asyncio.run(insert_async())


def data(dbfilepath: str):
    SCHEMA = """
    CREATE TABLE measurement_types (
        type_id   INTEGER PRIMARY KEY,
        name      TEXT NOT NULL UNIQUE COLLATE NOCASE
    );

    CREATE TABLE measurements (
        timestamp   UNIXTIME NOT NULL,
        device_name TEXT NOT NULL COLLATE NOCASE,
        sensor_id   INTEGER NOT NULL,
        type_id     INTEGER NOT NULL,
        value       REAL NOT NULL,
        FOREIGN KEY(type_id) REFERENCES measurement_types(type_id)
    );

    CREATE INDEX idx_measurements_timestamp ON measurements (timestamp);
    CREATE INDEX idx_measurements_sensor ON measurements (sensor_id);
    CREATE INDEX idx_measurements_sensor_type_time ON measurements (sensor_id, type_id, timestamp);
    CREATE INDEX idx_measurements_type_time ON measurements (type_id, timestamp);
    """

    from appdata.shared import MeasurementTypes

    with sqlite3.connect(dbfilepath) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR IGNORE INTO measurement_types (type_id, name) VALUES (?, ?)",
            ((m.value, m.name.lower()) for m in MeasurementTypes),
        )
        conn.commit()


def app(dbfilepath: str):
    SCHEMA_FILEPATH = "./services/api/storage/db/sql/schema.sql"

    from services.api.core import enums
    from services.api.storage.db.repositories.user_account_repository import (
        UserAccountRepository,
    )
    from services.api.storage.db.repositories.user_role_repository import (
        UserRoleRepository,
    )
    from services.api.storage.db.sql import sqlite

    with sqlite3.connect(dbfilepath) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA temp_store = MEMORY")
        with open(SCHEMA_FILEPATH) as f:
            conn.executescript(f.read())
        conn.executemany("INSERT INTO role (name) VALUES (?)", [(r,) for r in enums.UserRoles])
        conn.commit()

    db = sqlite.SQLite(dbfilepath)

    async def insert_async():
        repo_account = UserAccountRepository(db)
        repo_role = UserRoleRepository(db)
        try:
            for user in CONFIG["api"]["users"]:
                roles = [enums.UserRoles(role) for role in user["roles"]]
                user_id = await repo_account.create_user(
                    login_name=user["name"],
                    login_mail=None,
                    password_hash=helpers.hash_password_b64(user["password"]),
                    enabled=True,
                    created_by=None,
                )
                await asyncio.gather(
                    *(
                        repo_role.insert_user_role(
                            user_id=user_id,
                            role=role,
                            valid_from=None,
                            valid_to=None,
                            given_by=None,
                        )
                        for role in roles
                    )
                )
        except Exception as e:
            print("exc", e, file=sys.stderr)
        finally:
            await db.close()

    asyncio.run(insert_async())


if __name__ == "__main__":
    run()
