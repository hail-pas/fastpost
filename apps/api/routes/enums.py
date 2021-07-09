import inspect

from fastapi import Query, Depends, APIRouter
from starlette.requests import Request

from db import enums
from fastpost import resp_code
from fastpost.response import Resp
from fastpost.exceptions import NotFoundException

router = APIRouter(prefix="/curd")


def get_enum_content(request: Request, enum_name: str = Query(None, description="码表名字", example="GeneralStatus")):
    enum_content = {}
    enum_list = []
    if enum_name:
        try:
            enum_obj = getattr(enums, enum_name) or getattr(resp_code, enum_name)
            enum_list.append((enum_name, enum_obj))
        except (AttributeError, NotImplementedError):
            raise NotFoundException()
    else:
        enum_list = inspect.getmembers(enums) + inspect.getmembers(resp_code)

    for name, obj in enum_list:
        if inspect.isclass(obj):
            try:
                choices = obj.choices()
                format_ = request.scope["path"].split("/")[-1]
                if format_ == "list":
                    enum_content[name] = list(zip(choices.keys(), choices.values()))
                else:
                    enum_content[name] = obj.choices()
            except Exception:
                pass

    return enum_content


@router.get("/enums/list", description="枚举-列表", summary="枚举表", response_model=Resp[dict])
async def enum_content_list(enum_content=Depends(get_enum_content)):
    return Resp[dict](data=enum_content)


@router.get("/enums/json", description="枚举-JSON", summary="枚举表", response_model=Resp[dict])
async def enum_content_json(enum_content=Depends(get_enum_content)):
    return Resp[dict](data=enum_content)
