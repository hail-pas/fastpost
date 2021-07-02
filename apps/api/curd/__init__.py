from fastapi import APIRouter
from starlette.responses import JSONResponse

from apps.api.curd import view
from fastpost.response import AesResponse
from fastpost.settings import get_settings

curd_router = api_router = APIRouter(
    prefix="", default_response_class=JSONResponse if get_settings().DEBUG else AesResponse,
)

api_router.include_router(view.router, tags=["增删改查"])
