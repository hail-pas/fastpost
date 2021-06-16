import re

import sqlalchemy
from sqlalchemy.orm import sessionmaker, declared_attr, declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from fastpost.settings import get_settings


def create_engine():
    return create_async_engine(
        get_settings().POSTGRES_DATABASE_URL_ASYNC, echo=True, pool_timeout=30, pool_pre_ping=True, future=True,
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


class BaseModel:
    id = sqlalchemy.Column(comment="ID", type_=sqlalchemy.Integer, primary_key=True, index=True)
    created_at = sqlalchemy.Column(comment="创建时间", type_=sqlalchemy.TIMESTAMP)
    updated_at = sqlalchemy.Column(comment="更新时间", type_=sqlalchemy.DateTime, nullable=False)

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return "_".join([i.lower() for i in re.findall('[A-Z][^A-Z]*', cls.__name__)])


"""
Brief for SQLAlchemy

Manipulate:Insert, Select, Update, Delete


 
"""
