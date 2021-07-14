"""
HTTP API
"""
from fastapi import Depends, APIRouter

from apps.api.routes import auth, user, enums, common
from apps.dependencies import jwt_required

api_router = APIRouter(prefix="")

api_router.include_router(auth.router, prefix="/auth", tags=["授权相关"])
api_router.include_router(user.router, prefix="/user", tags=["用户信息管理"], dependencies=[Depends(jwt_required)])
api_router.include_router(enums.router, prefix="/enums", tags=["码表映射"])
api_router.include_router(common.router, prefix="/other", tags=["其他"])
