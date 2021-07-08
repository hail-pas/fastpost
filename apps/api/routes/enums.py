import inspect

from fastapi import Query, APIRouter

from db import enums
from fastpost.response import Resp
from fastpost.exceptions import NotFoundException

router = APIRouter(prefix="/curd")


@router.get("/enums/list", description="枚举-列表", summary="枚举表", response_model=Resp[dict])
async def enum_list(enum_name: str = Query(None, description="码表名字", example="GeneralStatus")):
    ret = {}
    ele_list = []
    if enum_name:
        try:
            enum_obj = getattr(enums, enum_name)
            ele_list.append((enum_name, enum_obj))
        except (AttributeError, NotImplementedError):
            raise NotFoundException()
    else:
        ele_list = inspect.getmembers(enums)

    for name, obj in ele_list:
        if inspect.isclass(obj):
            try:
                choices = obj.choices()
                ret[name] = list(zip(choices.keys(), choices.values()))
            except Exception:
                pass
    return Resp[dict](data=ret)


@router.get("/enums/json", description="枚举-JSON", summary="枚举表", response_model=Resp[dict])
async def enum_json(enum_name: str = Query(None, description="码表名字", example="GeneralStatus")):
    ret = {}
    ele_list = []
    if enum_name:
        try:
            enum_obj = getattr(enums, enum_name)
            ele_list.append((enum_name, enum_obj))
        except (AttributeError, NotImplementedError):
            raise NotFoundException()
    else:
        ele_list = inspect.getmembers(enums)
    for name, obj in ele_list:
        if inspect.isclass(obj):
            try:
                ret[name] = obj.choices()
            except Exception:
                pass
    return Resp[dict](data=ret)
