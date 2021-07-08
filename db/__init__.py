from typing import Any, List, Optional

from tortoise import Model, BaseDBAsyncClient, fields
from tortoise.models import ModelMeta
from tortoise.query_utils import Q
from tortoise.contrib.pydantic import pydantic_model_creator

from fastpost.types import Pager
from fastpost.response import generate_page_info
from fastpost.settings import get_settings

TORTOISE_ORM_CONFIG = get_settings().TORTOISE_ORM_CONFIG


class BaseModelMeta(ModelMeta):
    @property
    def response_model(cls):
        return pydantic_model_creator(cls)


class BaseModel(Model, metaclass=BaseModelMeta):
    id = fields.BigIntField(description="主键", pk=True)
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        abstract = True
        ordering = ["-id"]

    async def save(
        self,
        using_db: Optional[BaseDBAsyncClient] = None,
        update_fields: Optional[List[str]] = None,
        force_create: bool = False,
        force_update: bool = False,
    ) -> None:
        if update_fields:
            update_fields.append("updated_at")
        await super(BaseModel, self).save(using_db, update_fields, force_create, force_update)

    @classmethod
    async def page_data(
        cls, pager: Pager, *args: Q, **kwargs: Any,
    ):
        queryset = cls.filter(*args, **kwargs)
        page_info = generate_page_info(await queryset.count(), pager)
        data = await queryset.limit(pager.limit).offset(pager.offset)
        return page_info, data
