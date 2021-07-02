import inspect

from fastapi import Depends, APIRouter

from db import enums, models
from fastpost.types import Pager
from apps.dependencies import get_pager
from fastpost.response import Resp, PageResp, SimpleSuccess
from apps.api.curd.dependencies import ModelGetter

router = APIRouter(prefix="/curd")

curd_models = [models.User, models.Address, models.Profile, models.Group, models.Permission]

for model in curd_models:

    @router.post(
        path=f"/create/{model.__tablename__}", response_model=Resp[model.response_model], description="新增", summary="增"
    )
    async def create_model_func(
        data: model.create_schema, create_model=Depends(ModelGetter(model)),
    ):
        return await create_model.create(**data.dict())

    @router.delete(
        path=f"/delete/{model.__tablename__}" + "/{pk}", response_model=SimpleSuccess, description="删除", summary="删"
    )
    async def delete_model_func(
        pk, delete_model=Depends(ModelGetter(model)),
    ):
        await delete_model.delete_with_pk(pk)
        return SimpleSuccess()

    @router.put(
        path=f"/change/{model.__tablename__}" + "/{pk}",
        response_model=Resp[model.response_model],
        description="修改",
        summary="改",
    )
    async def change_model_func(
        pk, data: model.update_schema, change_model=Depends(ModelGetter(model)),
    ):
        await change_model.update_with_pk(pk, {k: v for k, v in data.dict().items() if v is not None})
        return SimpleSuccess()

    @router.get(
        path=f"/get/{model.__tablename__}", response_model=PageResp[model.response_model], description="获取", summary="查"
    )
    async def get_models_func(query_model=Depends(ModelGetter(model)), pager: Pager = Depends(get_pager)):
        page_info, data = await query_model.page_data(pager=pager)
        return PageResp[query_model.response_model](page_info=page_info, data=data)


@router.get("/enums/list", description="枚举表", summary="枚举表", response_model=Resp[dict])
async def enum_list():
    ret = {}
    for name, obj in inspect.getmembers(enums):
        if inspect.isclass(obj):
            try:
                choices = obj.choices()
                ret[name] = list(zip(choices.keys(), choices.values()))
            except Exception:
                pass
    return Resp[dict](data=ret)


@router.get("/enums/json", description="枚举表", summary="枚举表", response_model=Resp[dict])
async def enum_json():
    ret = {}
    for name, obj in inspect.getmembers(enums):
        if inspect.isclass(obj):
            try:
                ret[name] = obj.choices()
            except Exception:
                pass
    return Resp[dict](data=ret)
