from typing import Optional

from starlette.requests import Request
from starlette.exceptions import HTTPException

from fastpost.response import AesResponse
from fastpost.resp_code import ResponseCodeEnum


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    http 状态码非 200 的错误
    :param request:
    :param exc:
    :return:
    """
    return AesResponse(content={"code": int(f"100{exc.status_code}"), "message": exc.detail, "data": None})


class ApiException(Exception):
    """
    非 100200 的业务错误
    """

    code: Optional[int] = None
    message: Optional[str] = None

    def __init__(self, message: str = None, code: int = None):
        self.code = code or self.code
        self.message = message or self.message

    def to_result(self):
        assert self.code, "Response Must Have Response Code"
        return AesResponse(content={"code": self.code, "message": self.message, "data": None})


class NotAuthorizedException(ApiException):
    code = ResponseCodeEnum.NotAuthorized.value
    message = ResponseCodeEnum.NotAuthorized.label


class TokenInvalidException(ApiException):
    code = ResponseCodeEnum.TokenInvalid.value
    message = ResponseCodeEnum.TokenInvalid.label


class TokenExpiredException(ApiException):
    code = ResponseCodeEnum.TokenExpired.value
    message = ResponseCodeEnum.TokenExpired.label


class PermissionDenyException(ApiException):
    code = ResponseCodeEnum.PermissionDeny.value
    message = ResponseCodeEnum.PermissionDeny.label


class TimeStampExpiredException(ApiException):
    code = ResponseCodeEnum.TimeStampExpired.value
    message = ResponseCodeEnum.TimeStampExpired.label


class SignCheckFailedException(ApiException):
    code = ResponseCodeEnum.SignCheckFailed.value
    message = ResponseCodeEnum.SignCheckFailed.label


class NotFoundException(ApiException):
    code = 100404
    message = "不存在"


roster = [
    http_exception_handler,
]
