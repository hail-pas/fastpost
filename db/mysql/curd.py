"""
common database operation
"""
from db.mysql import enums, models


async def get_config_value_by_key(key, default=None):
    """
    获取在线参数
    :param default:
    :param key:
    :return:
    """
    if default is None:
        default = {}
    config = await models.Config.get_or_none(key=key, status=enums.GeneralStatus.on)
    if not config:
        return default
    return config.value
