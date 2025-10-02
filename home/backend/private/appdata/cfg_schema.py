from typing import Literal, TypedDict


class FileKeySSH(TypedDict):
    user: str
    port: int


class FileKeyMail(TypedDict):
    user: str
    password: str
    host: str
    port: int


class FileKeyFTP(TypedDict):
    host: str
    user: str
    passwd: str
    home_dir: str
    ftp_folder: str


class FileKeyDDNS(TypedDict):
    address: str
    path: str
    domain: str
    token: str


class FileKeyAPI_User(TypedDict):
    name: str
    password: str
    roles: list[str]  # models.UserRolesEnum | InternalRolesEnum


class FileKeyAPI_MQTT_External(TypedDict):
    username: str
    port: int


class FileKeyAPI_MQTT_Internal(TypedDict):
    username: str
    hostname: str
    port: int


# class FileKeyMQTT_Balcony_Command(TypedDict):
#     remaining: Literal["remaining"]  # For the command


class FileKeyMQTT_Balcony(TypedDict):
    relays: int  # e.g. 4
    path: Literal["relay"]  # e.g. "relay"
    # command: FileKeyMQTT_Balcony_Command


class FileKeyMQTT_Publish(TypedDict):
    balcony: FileKeyMQTT_Balcony


class FileKeyMQTT(TypedDict):
    external: FileKeyAPI_MQTT_External
    internal: FileKeyAPI_MQTT_Internal
    internal_subs: list[str]
    publish: FileKeyMQTT_Publish


class FileKeyAPI(TypedDict):
    users: list[FileKeyAPI_User]
    internal_users: list[FileKeyAPI_User]


class FileData(TypedDict):
    current_loc: str
    other_loc: list[str]
    hostname: str
    ssh: FileKeySSH
    mail: FileKeyMail
    ftp: FileKeyFTP
    ddns: FileKeyDDNS
    api: FileKeyAPI
    mqtt: FileKeyMQTT


FILENAME = "default.toml"


def load_file(path: str = FILENAME) -> FileData:
    import tomllib

    with open(path, "rb") as f:
        return tomllib.load(f)  # pyright: ignore[reportReturnType]
