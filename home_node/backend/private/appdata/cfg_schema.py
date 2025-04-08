from typing import TypedDict


class FileKeySSH(TypedDict):
    user: str
    port: int


class FileKeyMail(TypedDict):
    user: str
    password: str
    host: str
    relay: str
    port: int


class FileKeyFTP(TypedDict):
    host: str
    port: int
    user: str
    passwd: str
    workdir: str
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


class FileKeyMQTT(TypedDict):
    external: FileKeyAPI_MQTT_External
    internal: FileKeyAPI_MQTT_Internal
    internal_subs: list[str]


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
