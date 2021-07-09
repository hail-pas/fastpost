"""
HTTP API
"""
from fastapi import Depends, APIRouter

from apps.api.routes import auth, user, enums
from apps.dependencies import jwt_required

api_router = APIRouter(prefix="")

api_router.include_router(auth.router, tags=["授权相关"])
api_router.include_router(user.router, tags=["用户信息管理"], dependencies=[Depends(jwt_required)])
api_router.include_router(enums.router, tags=["码表映射"])
