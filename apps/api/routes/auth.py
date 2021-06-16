from typing import Any, Optional

from fastapi import Body, APIRouter
from pydantic import BaseModel
from pydantic.errors import MissingError
from sqlalchemy import or_
from sqlalchemy.future import select

from common.encrypt import Jwt
from db import db
from db.models import User
from fastpost.exceptions import NotFoundException
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
    id: int
    username: str
    phone: str
    token_type: Optional[str]
    token_value: Optional[str]

    class Config:
        orm_mode = True


"""
3. view_func
"""


@router.post("/login", summary="登录", description="登录接口", response_model=Resp[AuthData])
async def login(login_data: LoginSchema):
    user = (await db.session.execute(select(User).filter(
        or_(User.username == login_data.username, User.phone == login_data.phone)))).scalars().first()
    if not user:
        raise NotFoundException("用户不存在")
    data = AuthData.from_orm(user).dict()
    data["token_type"] = "Bearer"
    data["token_value"] = Jwt(get_settings().JWT_SECRET).get_jwt(
        {"user_id": user.id, })  # "exp": get_settings().JWT_TOKEN_EXPIRE_MINUTES
    return Resp[AuthData](data=data)
