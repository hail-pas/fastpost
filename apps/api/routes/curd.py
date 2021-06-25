from fastapi import APIRouter

from db import models
from fastpost.response import Resp, PageResp

router = APIRouter(prefix="/curd")


@router.post("/create/Address", summary="增删改查", description="数据模型增删改查", )
def create_model(data: models.Address.create_schema):
    return


@router.post("/create/User", summary="增删改查", description="数据模型增删改查")
def create_model(data: models.User.create_schema):
    return
