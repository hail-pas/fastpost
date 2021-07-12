import time
from typing import Optional
from urllib.parse import unquote

from jose import jwt
from fastapi import Query, Header, Depends
from pydantic import PositiveInt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_403_FORBIDDEN, HTTP_406_NOT_ACCEPTABLE
from starlette.requests import Request
from starlette.exceptions import HTTPException
from fastapi.security.utils import get_authorization_scheme_param

from common.utils import get_client_ip
from common.encrypt import Jwt, SignAuth
from db.mysql.models import User
from fastpost.schema import Pager
from fastpost.globals import g
from fastpost.settings import settings
from fastpost.exceptions import (
    TokenExpiredException,
    TokenInvalidException,
    NotAuthorizedException,
    SignCheckFailedException,
    TimeStampExpiredException,
)


class TheBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        authorization: str = request.headers.get("Authorization")
        if not authorization:
            raise NotAuthorizedException("未携带授权头部信息")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise NotAuthorizedException("授权头部信息有误")
            else:
                return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise NotAuthorizedException(message="授权信息类型错误，请使用bearer")
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


auth_schema = TheBearer()


def get_pager(
    page: PositiveInt = Query(default=1, example=1, description="第几页"),
    size: PositiveInt = Query(default=10, example=10, description="每页数量"),
):
    return Pager(limit=size, offset=(page - 1) * size)


async def jwt_required(request: Request, token: HTTPAuthorizationCredentials = Depends(auth_schema)):
    jwt_secret: str = settings.JWT_SECRET
    try:
        payload = Jwt(jwt_secret).decode(token.credentials)
        user_id = payload.get("user_id")
        if user_id is None:
            raise TokenInvalidException()
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except jwt.JWTError:
        raise TokenInvalidException()
    # 初始化全局用户信息，后续处理函数中直接使用
    user = await User.get_or_none(id=user_id)
    if not user:
        raise TokenInvalidException()
    g.user = user
    request.scope["user"] = user
    return user


async def sign_check(
    request: Request,
    x_timestamp: int = Header(..., example=int(time.time()), description="秒级时间戳"),
    x_signature: str = Header(..., example="sign", description="签名"),
):
    if request.method in ["GET", "DELETE"]:
        sign_str = request.scope["query_string"].decode()
        sign_str = unquote(sign_str)
    else:
        try:
            sign_str = await request.body()
            sign_str = sign_str.decode()
        except Exception:
            raise HTTPException(HTTP_406_NOT_ACCEPTABLE, "json body required")
    sign_str = sign_str + f".{x_timestamp}"
    if not settings.DEBUG:
        if int(time.time()) - x_timestamp > 60:
            raise TimeStampExpiredException()
        if not x_signature or not SignAuth(settings.SIGN_SECRET).verify(x_signature, sign_str):
            raise SignCheckFailedException()


async def host_checker(request: Request,):
    if "*" in settings.ALLOWED_HOST_LIST:
        return
    caller_host = get_client_ip(request)
    if "." in caller_host:
        host_segments = caller_host.strip().split(".")
        if len(host_segments) == 4:
            blur_segments = ["*", "*", "*", "*"]
            for i in range(4):
                blur_segments[i] = host_segments[i]
                if ".".join(blur_segments) in settings.ALLOWED_HOST_LIST:
                    return
    raise HTTPException(HTTP_403_FORBIDDEN, f"IP {caller_host} 不在访问白名单")
