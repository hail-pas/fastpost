from enum import Enum, unique


@unique
class ResponseCodeEnum(int, Enum):
    """
    业务响应代码，除了500之外都在200的前提下返回对用code
    """

    def __new__(cls, value, label):
        obj = int.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj

    # 唯一成功响应
    Success = (100200, "成功")

    # HTTP 状态码  2xx - 5xx
    # 100{[2-5]]xx}, http status code 拼接

    # 异常响应，999倒序取
    Failed = (100999, "失败")
    NotAuthorized = (100998, "未授权")
    TokenInvalid = (100997, "无效Token")
    TokenExpired = (100996, "过期Token")
    PermissionDeny = (100995, "权限不足")
    TimeStampExpired = (100994, "时间戳过期")
    SignCheckFailed = (100993, "Sign校验失败")

    @classmethod
    def items(cls):
        return {item.value: item.label for item in cls}
