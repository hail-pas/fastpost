from typing import Any
from datetime import datetime, timedelta

from fastapi import Body, Depends, APIRouter
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from pydantic.errors import MissingError

from db.models import User
from common.encrypt import Jwt
from fastpost.globals import g
from apps.dependencies import jwt_required
from fastpost.response import Resp, SimpleSuccess
from fastpost.settings import get_settings
from fastpost.exceptions import NotFoundException, CommonFailedException

router = APIRouter(prefix="/auth")

"""
1. request_schema
"""


class LoginSchema(BaseModel):
    phone: str = Body(None, description="手机号", example="18888888888")
    username: str = Body(None, description="用户名", example="phoenix")
    password: str = Body(..., description="密码")

    @classmethod
    def validate(cls, value: Any):
        if not isinstance(value, dict):
            value = dict(value)

        if not value.get("phone") and not value.get("username"):
            raise MissingError(msg_template="phone and username cannot both be empty")
        return cls(**value)


"""
2. response_schema
"""


class AuthData(BaseModel):
    token_type: str
    token_value: str
    expired_at: datetime

    class Config:
        orm_mode = True


"""
3. view_func
"""


@router.post("/login", summary="登录", description="登录接口", response_model=Resp[AuthData])
async def login(login_data: LoginSchema):
    user = await User.filter(
        or_(User.username == login_data.username, User.phone == login_data.phone)
    ).first()  # type: User
    if not user:
        raise NotFoundException("用户不存在")
    user.last_login_at = datetime.now()
    await user.save(update_fields=["last_login_at"])
    expired_at = datetime.now() + timedelta(minutes=get_settings().JWT_TOKEN_EXPIRE_MINUTES)
    data = {
        "token_type": "Bearer",
        "token_value": Jwt(get_settings().JWT_SECRET).get_jwt({"user_id": user.id, "exp": expired_at}),
        "expired_at": expired_at,
    }
    return Resp[AuthData](data=data)


@router.post(
    "/token/refresh",
    summary="刷新token",
    description="刷新token过期时间",
    response_model=Resp[AuthData],
    dependencies=[Depends(jwt_required)],
)
async def refresh_token():
    expired_at = datetime.now() + timedelta(minutes=get_settings().JWT_TOKEN_EXPIRE_MINUTES)
    data = {
        "token_type": "Bearer",
        "token_value": Jwt(get_settings().JWT_SECRET).get_jwt({"user_id": g.user.id, "exp": expired_at}),
        "expired_at": expired_at,
    }
    return Resp[AuthData](data=data)


@router.post(
    "/logout", summary="登出", description="退出登录接口", response_model=SimpleSuccess, dependencies=[Depends(jwt_required)]
)
async def logout():
    return


class RegisterIn(BaseModel):
    phone: str = Body(None, description="手机号", example="18888888888")
    username: str = Body(None, description="用户名", example="phoenix")
    password: str = Body(..., description="密码")


@router.post("/register", summary="用户注册", description="新用户注册接口", response_model=Resp[User.response_model])
async def register(register_in: RegisterIn):
    try:
        user = await User.create(**register_in.dict())
    except IntegrityError:
        raise CommonFailedException("用户已存在")
    return Resp[User.response_model](data=user)
