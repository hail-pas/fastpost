from fastapi import Query, APIRouter

from db.mysql import enums
from db.mysql.models import Config
from fastpost.response import PageResp

router = APIRouter()


@router.get("/config/info", summary="config信息", description="动态配置", response_model=PageResp[Config.response_model])
async def config_info(key: str = Query(None, description="在线参数key", example="task_config")):
    filter_ = dict(status=enums.GeneralStatus.on, safe=True)
    if key:
        filter_["key"] = key
    config = await Config.filter(**filter_)
    return PageResp[Config.response_model](data=config)
