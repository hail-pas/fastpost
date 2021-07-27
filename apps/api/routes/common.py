from fastapi import File, Form, Query, APIRouter, UploadFile

from db.mysql import enums
from core.response import Resp, PageResp
from db.mysql.models import Config

router = APIRouter()


@router.get("/config/info", summary="config信息", description="动态配置", response_model=PageResp[Config.response_model])
async def config_info(key: str = Query(None, description="在线参数key", example="task_config")):
    filter_ = dict(status=enums.GeneralStatus.on, safe=True)
    if key:
        filter_["key"] = key
    config = await Config.filter(**filter_)
    return PageResp[Config.response_model](data=config)


@router.post("/upload", summary="上传", description="文件上传", response_model=Resp)
async def upload(filename: str = Form(...), file: UploadFile = File(...)):
    return Resp(data={"filename": filename, "file": file.filename})
