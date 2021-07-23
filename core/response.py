import logging
from math import ceil
from typing import List, Generic, TypeVar, Optional
from datetime import datetime

from pydantic import BaseModel, typing, validator
from pydantic.generics import GenericModel
from starlette.responses import JSONResponse

from core.schema import Pager
from common.utils import datetime_now
from core.resp_code import ResponseCodeEnum

logger = logging.getLogger(__name__)


class AesResponse(JSONResponse):
    """"
    响应：
    res = {
        "code": 100200,
        "responseTime": "datetime",
        "message": "message",  # 当code不等于100200表示业务错误，该字段返回错误信息
        "data": "data"    # 当code等于100200表示正常调用，该字段返回正常结果
        }
    不直接使用该Response， 使用下面的响应Model - 具有校验/生成文档的功能
    """

    def __init__(self, content: typing.Any = None, status_code=200, **kwargs):
        super().__init__(content, status_code=status_code, **kwargs)

    def render(self, content: typing.Any) -> bytes:
        # update responseTime
        content["responseTime"] = datetime_now().isoformat(sep="T")
        # if not get_settings().DEBUG:
        #     content = AESUtil(get_settings().AES_SECRET).encrypt_data(ujson.dumps(content))
        return super(AesResponse, self).render(content)


DataT = TypeVar("DataT")


class Resp(GenericModel, Generic[DataT]):
    """
    响应Model
    """

    code: int = ResponseCodeEnum.Success.value
    responseTime: datetime = None
    message: Optional[str] = None
    data: Optional[DataT] = None

    @validator("data", always=True)
    def check_consistency(cls, v, values):
        if values.get("message") is None and values.get("code") != ResponseCodeEnum.Success.value:
            raise ValueError(f"Must provide a message when code is not {ResponseCodeEnum.Success.value}!")
        if values.get("message") and v:
            raise ValueError("Response can't provide both message and data!")
        return v


class SimpleSuccess(Resp):
    """
    简单响应成功
    """


class PageInfo(BaseModel):
    """
    翻页相关信息
    """

    total_page: int
    total_count: int
    size: int
    page: int


class PageResp(Resp, Generic[DataT]):
    page_info: PageInfo = None
    data: Optional[List[DataT]] = None


def generate_page_info(total_count, pager: Pager):
    return PageInfo(
        total_page=ceil(total_count / pager.limit),
        total_count=total_count,
        size=pager.limit,
        page=pager.offset // pager.limit + 1,
    )
