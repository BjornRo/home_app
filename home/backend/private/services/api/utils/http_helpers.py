from core import constants
from litestar import MediaType, Request, Response
from litestar.connection import ASGIConnection, Request
from litestar.datastructures.cookie import Cookie
from litestar.datastructures.headers import Headers

resp401 = Response({"status_code": 401, "detail": "Unauthorized"}, media_type=MediaType.JSON, status_code=401)


def get_token_str(headers: Headers) -> str | None:
    try:
        prefix, token_str = headers["Authorization"].split(" ", 2)
        if prefix.lower() == "bearer":
            return token_str
    except:
        pass
    return None


def http_401_resp(request: Request, exc: Exception) -> Response:
    return resp401


def is_local_request(conn: ASGIConnection) -> bool:
    return constants.HEADER_SERVICE_KEY not in conn.headers


def create_refresh_cookie(refresh_token: str, expiry: int):
    return Cookie(
        key=constants.REFRESH_TOKEN,
        value=refresh_token,
        expires=expiry,
        path="/auth/",
        httponly=True,
        secure=True,
        samesite="lax",
    )


def create_access_cookie(access_token: str, expiry: int):
    return Cookie(
        key=constants.ACCESS_TOKEN,
        value=access_token,
        expires=expiry,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
