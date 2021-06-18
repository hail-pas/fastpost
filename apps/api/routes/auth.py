from datetime import timedelta, datetime
from typing import Any

from fastapi import Body, APIRouter, Depends
from pydantic import BaseModel
from pydantic.errors import MissingError
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from apps.depends import jwt_required
from common.encrypt import Jwt
from db import db
from db.models import User
from fastpost.exceptions import NotFoundException
from fastpost.globals import g
from fastpost.response import Resp
from fastpost.settings import get_settings

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
    user = (await db.session.execute(select(User).options(joinedload(User.addresses)).filter(
        or_(User.username == login_data.username, User.phone == login_data.phone)))).scalars().first()
    if not user:
        raise NotFoundException("用户不存在")
    expired_at = datetime.now() + timedelta(minutes=get_settings().JWT_TOKEN_EXPIRE_MINUTES)
    data = {
        "token_type": "Bearer",
        "token_value": Jwt(get_settings().JWT_SECRET).get_jwt(
            {"user_id": user.id, "exp": expired_at}),
        "expired_at": expired_at
    }
    return Resp[AuthData](data=data)


@router.post("/token/refresh", summary="刷新token", description="刷新token过期时间", response_model=Resp[AuthData],
             dependencies=[Depends(jwt_required)])
async def refresh_token():
    expired_at = datetime.now() + timedelta(minutes=get_settings().JWT_TOKEN_EXPIRE_MINUTES)
    data = {
        "token_type": "Bearer",
        "token_value": Jwt(get_settings().JWT_SECRET).get_jwt(
            {"user_id": g.user.id, "exp": expired_at}),
        "expired_at": expired_at
    }
    return Resp[AuthData](data=data)
