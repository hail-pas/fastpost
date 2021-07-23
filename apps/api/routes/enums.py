import inspect
from typing import Dict, Tuple, Union

from fastapi import Query, Depends, APIRouter
from starlette.requests import Request

from core import resp_code
from db.mysql import enums
from core.response import Resp
from core.exceptions import NotFoundException

router = APIRouter()


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
        if name in ["StrEnumMore", "IntEnumMore"]:
            continue
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


@router.get(
    "/list",
    description="枚举-列表",
    summary="枚举表",
    response_model=Resp[Dict[str, Tuple[Tuple[Union[int, str], Union[int, str]], ...]]],
)
async def enum_content_list(enum_content=Depends(get_enum_content)):
    return Resp[dict](data=enum_content)


@router.get(
    "/json",
    description="枚举-JSON",
    summary="枚举表",
    response_model=Resp[Dict[str, Dict[Union[int, str], Union[int, str]]]],
)
async def enum_content_json(enum_content=Depends(get_enum_content)):
    return Resp[dict](data=enum_content)
