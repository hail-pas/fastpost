import abc
import re
from datetime import datetime
from typing import Optional, Any, Type, TypeVar, List

import sqlalchemy
from pydantic import create_model, BaseConfig
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import sessionmaker, declared_attr, declarative_base, DeclarativeMeta, ColumnProperty, \
    RelationshipProperty, joinedload
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from fastpost.response import generate_page_info
from fastpost.settings import get_settings
from fastpost.types import Pager


def create_engine():
    return create_async_engine(
        get_settings().POSTGRES_DATABASE_URL_ASYNC, echo=get_settings().DEBUG, pool_timeout=30, pool_pre_ping=True,
        future=True,
    )


class SQLAlchemy:
    def __init__(self):
        self.Model = declarative_base()
        self.engine = create_engine()
        self.session: AsyncSession = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)()

    def create_all(self, connection):
        return self.Model.metadata.create_all(bind=connection)

    def drop_all(self, connection):
        return self.Model.metadata.drop_all(bind=connection)


db = SQLAlchemy()


class PydanticCreateMeta(DeclarativeMeta, abc.ABCMeta):
    PyModel = TypeVar('PyModel', bound='BaseModel')
    common_column = ["id", "created_at", "updated_at"]

    @property
    def response_model(cls) -> Type['PyModel']:
        """
        自动生成 pydantic_model 用于数据序列化, 不包括外键
        class Config:
            excludes = ()
            computed = ()
        :return:
        """

        def generate_response_model(model, recursive):
            if recursive > 2:
                return

            class Config(BaseConfig):
                orm_mode = True

            kwargs = {
                "id": (int, ...)
            }
            config = getattr(model, "Config")
            mapper = inspect(model)
            for attr in mapper.attrs:
                if isinstance(attr, ColumnProperty):
                    if attr.columns:
                        column_name = attr.key
                        if (column_name in model.common_column) or (column_name.endswith("_id")) or (
                                config and column_name in getattr(config, "exclude", [])):
                            continue
                        column = attr.columns[0]
                        python_type: Optional[type] = None
                        if hasattr(column.type, "impl"):
                            if hasattr(column.type.impl, "python_type"):
                                python_type = column.type.impl.python_type
                        elif hasattr(column.type, "python_type"):
                            python_type = column.type.python_type
                        assert python_type, f"Could not infer python_type for {column}"
                        default = None
                        if column.default is None and not column.nullable:
                            default = ...
                        kwargs[column_name] = (python_type, default)
                # 关联对象
                # elif isinstance(attr, RelationshipProperty):
                #     type_ = generate_response_model(attr.mapper.class_, recursive + 1)
                #     if type_:
                #         if not attr.uselist:
                #             kwargs[attr.key] = (Optional[type_], None)
                #         else:
                #             kwargs[attr.key] = (Optional[List[type_]], [])

            if config:
                for additional in getattr(config, "additional", []):
                    if getattr(model, additional, None):
                        kwargs[additional] = (Optional[Any], None)
            kwargs["updated_at"] = (datetime, ...)
            kwargs["created_at"] = (datetime, ...)
            return create_model(f"{model.__name__}RespModel", __config__=Config, **kwargs)
        
        return generate_response_model(cls, 0)

    @property
    def create_schema(cls):
        kwargs = {}
        validators = {}
        for attr in inspect(cls).attrs:
            if isinstance(attr, ColumnProperty):
                if attr.columns:
                    column_name = attr.key
                    if column_name in cls.common_column:
                        continue
                    column = attr.columns[0]
                    python_type: Optional[type] = None
                    if hasattr(column.type, "impl"):
                        if hasattr(column.type.impl, "python_type"):
                            python_type = column.type.impl.python_type
                    elif hasattr(column.type, "python_type"):
                        python_type = column.type.python_type
                    assert python_type, f"Could not infer python_type for {column}"
                    default = None
                    if column.default is None and not column.nullable:
                        default = ...
                    kwargs[column_name] = (python_type, default)
            elif isinstance(attr, RelationshipProperty):
                if not attr.uselist:
                    kwargs[attr.key] = (Optional[int], None)
                else:
                    kwargs[attr.key] = (Optional[List[int]], None)
        return create_model(f"{cls.__name__}CreateSchema", __validators__=validators, **kwargs)


class BaseModel(db.Model, metaclass=PydanticCreateMeta):
    id = sqlalchemy.Column(comment="ID", type_=sqlalchemy.Integer, primary_key=True, index=True)
    created_at = sqlalchemy.Column(comment="创建时间", type_=sqlalchemy.DateTime, server_default=func.now(), )
    updated_at = sqlalchemy.Column(comment="更新时间", type_=sqlalchemy.DateTime, server_default=func.now(),
                                   onupdate=func.now())

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return "_".join([i.lower() for i in re.findall('[A-Z][^A-Z]*', cls.__name__)])

    __abstract__ = True

    @classmethod
    async def total(cls, **kwargs):
        total = (await db.session.execute(
            select([func.count(cls.id)]).select_from(cls).filter(*(getattr(cls, k) == v for k, v in kwargs.items()))
        )).scalar()
        return total

    @classmethod
    async def page_data(cls, pager: Pager, *join_loads, **kwargs):
        page_info = generate_page_info(await cls.total(**kwargs), pager)
        if join_loads:
            stmt = select(cls).options(
                joinedload(*[getattr(cls, attr) for attr in join_loads])).filter(
                *[getattr(cls, k) == v for k, v in kwargs.items()]).offset(pager.offset).limit(pager.limit)
        else:
            stmt = select(cls).filter(
                *[getattr(cls, k) == v for k, v in kwargs.items()]).offset(pager.offset).limit(pager.limit)
        data = (await db.session.execute(stmt)).scalars().all()
        return page_info, data

    class Config:
        """
        exclude, computed
        """
        exclude = []
        computed = []


"""
Brief for SQLAlchemy

Manipulate:Insert, Select, Update, Delete


 
"""
