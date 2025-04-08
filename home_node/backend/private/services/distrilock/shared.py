from enum import IntEnum
from struct import Struct

import msgspec

type ReturnResult = tuple[bool, bytes]

DEFAULT_UNIX_SOCK_ADDRESS = "/dev/shm/dlserver.sock"

response_protocol = Struct(">?H")  # Q: int_id, ?: Ok/Err, H: Header_len for data following

class RequestMethods(IntEnum):
    SIZE = 0
    KEYS = 1
    GET = 2
    SET = 3
    DELETE = 4
    UPDATE = 5


class Request(msgspec.Struct):
    index: int
    method: RequestMethods
    key: str
    expiry: int | None
    data_len: int | None

    def __post_init__(self):
        self.key = self.key.lower()
