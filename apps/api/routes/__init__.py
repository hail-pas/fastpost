from fastapi import Depends, APIRouter
from starlette.responses import JSONResponse

from apps.dependencies import jwt_required
from apps.api.routes import auth, user
from fastpost.response import AesResponse
from fastpost.settings import get_settings

api_router = APIRouter(prefix="", default_response_class=JSONResponse if get_settings().DEBUG else AesResponse,)

api_router.include_router(auth.router, tags=["授权相关"])
api_router.include_router(user.router, tags=["用户信息管理"], dependencies=[Depends(jwt_required)])
