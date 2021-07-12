from typing import Any, List, Optional

from tortoise import Model, BaseDBAsyncClient, fields
from tortoise.models import ModelMeta
from tortoise.query_utils import Q

from db.serializers import RecursionLimitPydanticMeta, pydantic_model_creator
from fastpost.schema import Pager
from fastpost.response import generate_page_info
from fastpost.settings import get_settings

TORTOISE_ORM_CONFIG = get_settings().TORTOISE_ORM_CONFIG


class BaseModelMeta(ModelMeta):
    @property
    def response_model(cls):
        # noinspection PyTypeChecker
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
        data = (
            await queryset.limit(pager.limit)
            .offset(pager.offset)
            .select_related(*cls.get_select_related_fields())
            .prefetch_related(*cls.get_prefetch_related_fields())
        )
        return page_info, data

    @classmethod
    def get_select_related_fields(cls) -> List[str]:
        select_related_fields = []
        pydantic_meta = getattr(cls, "PydanticMeta", RecursionLimitPydanticMeta)
        for field_name, field_desc in cls._meta.fields_map.items():
            if (
                (
                    isinstance(field_desc, fields.relational.ForeignKeyFieldInstance)
                    or isinstance(field_desc, fields.relational.OneToOneFieldInstance)
                )
                and field_name not in getattr(pydantic_meta, "exclude", ())
                and (not getattr(pydantic_meta, "include", ()) or field_name in getattr(pydantic_meta, "include", ()))
            ):
                select_related_fields.append(field_name)
        return select_related_fields

    @classmethod
    def get_prefetch_related_fields(cls) -> List[str]:
        prefetch_related_fields = []
        pydantic_meta = getattr(cls, "PydanticMeta", RecursionLimitPydanticMeta)
        for field_name, field_desc in cls._meta.fields_map.items():
            if (
                (
                    isinstance(field_desc, fields.relational.BackwardFKRelation)
                    or isinstance(field_desc, fields.relational.ManyToManyFieldInstance)
                    or isinstance(field_desc, fields.relational.BackwardOneToOneRelation)
                )
                and field_name not in getattr(pydantic_meta, "exclude", ())
                and (not getattr(pydantic_meta, "include", ()) or field_name in getattr(pydantic_meta, "include", ()))
            ):
                prefetch_related_fields.append(field_name)

        return prefetch_related_fields
