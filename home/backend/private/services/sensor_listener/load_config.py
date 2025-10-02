def load(data_path: str):
    from os import environ
    from ssl import SSLContext, create_default_context
    from tomllib import load as toml_load
    from typing import TypedDict, cast

    from appdata import cfg_schema

    with open(data_path + "default.toml", "rb") as f:
        cfg = cast(cfg_schema.FileData, toml_load(f))

    class MQTTExternal(cfg_schema.FileKeyAPI_MQTT_External):
        password: str
        identifier: str
        hostname: str
        tls_context: SSLContext

    class MQTTInternal(cfg_schema.FileKeyAPI_MQTT_Internal):
        password: str
        identifier: str
        tls_context: SSLContext

    class Config(TypedDict):
        ftp: cfg_schema.FileKeyFTP
        external: MQTTExternal
        internal: MQTTInternal
        subs: list[str]
        sshuser: str
        sshport: int
        other_loc: list[str]
        current_loc: str

    external = internal = None
    for usr in cfg["api"]["internal_users"]:
        if (_ext := cfg["mqtt"]["external"])["username"] == usr["name"]:
            external = MQTTExternal(
                **_ext,
                password=usr["password"],
                identifier=_ext["username"] + "_unit",
                tls_context=create_default_context(),
                hostname=cfg["hostname"],
            )
        elif (_int := cfg["mqtt"]["internal"])["username"] == usr["name"]:
            internal = MQTTInternal(
                **_int,
                password=usr["password"],
                identifier=_int["username"] + "_unit",
                tls_context=create_default_context(cafile=environ["CA_FILEPATH"]),
            )
        if external and internal:
            break
    else:
        raise Exception("Password not found in config file")

    return Config(
        ftp=cfg["ftp"],
        external=external,
        internal=internal,
        subs=cfg["mqtt"]["internal_subs"],
        sshuser=cfg["ssh"]["user"],
        sshport=cfg["ssh"]["port"],
        other_loc=cfg["other_loc"],
        current_loc=cfg["current_loc"],
    )
