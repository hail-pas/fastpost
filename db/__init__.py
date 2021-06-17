import abc
import re
from datetime import datetime
from typing import Optional, Any, Type, TypeVar

import sqlalchemy
from pydantic import create_model, BaseConfig
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker, declared_attr, declarative_base, DeclarativeMeta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from fastpost.settings import get_settings


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

    @property
    def response_model(cls) -> Type['PyModel']:
        """
        自动生成 pydantic_model 用于数据序列化
        class Config:
            excludes = ()
            computed = ()
        :return:
        """
        common_column = ["id", "created_at", "updated_at"]

        class Config(BaseConfig):
            orm_mode = True

        kwargs = {
            "id": (int, ...)
        }
        config = getattr(cls, "Config")
        for column_name, column in cls.__table__.columns.items():
            if column_name in common_column or (config and column_name in getattr(config, "excludes", [])):
                continue
            default = column.default
            if default is None and not column.nullable:
                default = ...
            kwargs[column_name] = (column.type.python_type, default)
        if config:
            for additional in getattr(config, "additional", []):
                if getattr(cls, additional, None):
                    kwargs[additional] = (Optional[Any], None)
        kwargs["updated_at"] = (datetime, ...)
        kwargs["created_at"] = (datetime, ...)
        return create_model(f"{cls.__name__}PydanticModel", __config__=Config, **kwargs)


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


"""
Brief for SQLAlchemy

Manipulate:Insert, Select, Update, Delete


 
"""
