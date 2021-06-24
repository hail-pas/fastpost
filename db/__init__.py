import abc
import re
from asyncio import current_task
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Any, Type, TypeVar, List, Union
from sqlalchemy import update

import sqlalchemy
from pydantic import create_model, BaseConfig
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import sessionmaker, declared_attr, declarative_base, DeclarativeMeta, ColumnProperty, \
    RelationshipProperty, joinedload
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_scoped_session
from sqlalchemy.ext.asyncio.result import AsyncScalarResult
from sqlalchemy.orm.clsregistry import _ModuleMarker
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql import ClauseElement

from fastpost.response import generate_page_info
from fastpost.settings import get_settings
from fastpost.types import Pager


# @event.listens_for(Engine, "before_cursor_execute")
# def before_cursor_execute(conn, cursor, statement,
#                          parameters, context, executemany):
#    conn.info.setdefault('query_start_time', []).append(time.time())
#    logger.debug("Start Query: %s", statement)


# @event.listens_for(Engine, "after_cursor_execute")
# def after_cursor_execute(conn, cursor, statement,
#                         parameters, context, executemany):
#    total = time.time() - conn.info['query_start_time'].pop(-1)
#    logger.debug("Query Complete!")
#    logger.debug("Total Time: %f", total)


def create_engine():
    return create_async_engine(
        get_settings().POSTGRES_DATABASE_URL_ASYNC, echo=not get_settings().DEBUG, pool_timeout=30, pool_pre_ping=True,
        max_overflow=0, pool_size=80 // get_settings().WORKERS, pool_recycle=3600, future=True,
    )


class SQLAlchemy:
    def __init__(self):
        self.Model = declarative_base()
        self.engine = create_engine()
        self.session_maker: sessionmaker = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    def create_all(self, connection):
        return self.Model.metadata.create_all(bind=connection)

    def drop_all(self, connection):
        return self.Model.metadata.drop_all(bind=connection)

    @asynccontextmanager
    async def session_ctx(self):
        db_session = async_scoped_session(self.session_maker, current_task)
        try:
            yield db_session  # type: AsyncSession
        finally:
            await db_session.close()

    def get_model_by_table_name(self, table):
        for c in self.Model.registry._class_registry.values():
            if isinstance(c, _ModuleMarker):
                continue
            if inspect(c).local_table == table:
                return c


db = SQLAlchemy()


class BaseModelMeta(DeclarativeMeta, abc.ABCMeta):
    PyModel = TypeVar('PyModel', bound='BaseModel')
    common_column = ["id", "created_at", "updated_at"]

    # BaseModel Relation

    # Pydantic
    @property
    def response_model(cls) -> Type['PyModel']:
        """
        自动生成 pydantic_model 用于数据序列化, 不包括外键
        class Config:
            excludes = ()
            additional = ()
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


class BaseModel(db.Model, metaclass=BaseModelMeta):
    id = sqlalchemy.Column(comment="ID", type_=sqlalchemy.Integer, primary_key=True, index=True)
    created_at = sqlalchemy.Column(comment="创建时间", type_=sqlalchemy.DateTime, server_default=func.now(), )
    updated_at = sqlalchemy.Column(comment="更新时间", type_=sqlalchemy.DateTime, server_default=func.now(),
                                   onupdate=func.now())

    # Generate table name automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return "_".join([i.lower() for i in re.findall('[A-Z][^A-Z]*', cls.__name__)])

    __abstract__ = True

    def __getattribute__(self, item):
        if item in [relation.key for relation in inspect(type(self)).relationships]:
            relation = getattr(inspect(type(self)).attrs, item)
            if not relation.uselist:
                return RelationObjectFilter(type(self), relation.mapper.class_, **{
                    f"{relation.primaryjoin.right.key}": self.to_dict().get(relation.primaryjoin.left.key)}).first()
            if relation.direction.name == "ONETOMANY":
                return RelationObjectFilter(type(self), relation.mapper.class_, **{
                    f"{relation.primaryjoin.right.key}": self.to_dict().get(relation.primaryjoin.left.key)}).all()
            if relation.direction.name == "MANYTOONE":
                return RelationObjectFilter(type(self), relation.mapper.class_, **{
                    f"{relation.primaryjoin.right.key}": self.to_dict().get(relation.primaryjoin.left.key)}).all()
            if relation.direction.name == "MANYTOMANY":
                return RelationObjectFilter(type(self), relation.mapper.class_).join(
                    db.get_model_by_table_name(relation.secondary),
                    getattr(relation.mapper.class_, relation.secondaryjoin.left.key) == getattr(
                        db.get_model_by_table_name(relation.secondary),
                        relation.secondaryjoin.right.key)).filter(
                    getattr(db.get_model_by_table_name(relation.secondary),
                            relation.secondaryjoin.right.key) == self.to_dict().get(
                        relation.secondaryjoin.left.key)).all()
        elif item in [f"{relation.key}_filter" for relation in inspect(type(self)).relationships]:
            relation = getattr(inspect(type(self)).attrs, item)
            return RelationObjectFilter(type(self), relation.mapper.class_, **{
                f"{relation.primaryjoin.right.key}": self.to_dict().get(relation.primaryjoin.left.key)})
        return super().__getattribute__(item)

    def __setattr__(self, key, value):
        if key in [relation.key for relation in inspect(type(self)).relationships]:
            raise Exception("Relationship set require add function of RelationObject")
        super(BaseModel, self).__setattr__(key, value)

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict["_sa_instance_state"]
        return model_dict

    def fill(self, **kwargs):
        mapper = inspect(self.__class__)
        for name in kwargs.keys():
            if name in [attr.key for attr in mapper.attrs]:
                setattr(self, name, kwargs[name])
            else:
                raise KeyError("Attribute '{}' doesn't exist".format(name))

        return self

    async def save(self, update_fields: List = None):
        if not update_fields:
            raise Exception("Must specify update_fields")
        if "id" in update_fields or "created_at" in update_fields:
            raise Exception("Cannot update id/created_at field")
        else:
            kwargs = {
                "updated_at": datetime.now()
            }
            self_dict = self.to_dict()
            for key in update_fields:
                if key not in self_dict.keys():
                    if key in [f"{relation.key}_filter" for relation in inspect(type(self)).relationships]:
                        # relationship_fields.append(key)
                        pass
                    else:
                        raise Exception(f"Field {key} doesn't exist")
                v = self_dict.get(key)
                kwargs[key] = v
        async with db.session_ctx() as session:
            await session.execute(update(self.__class__)
                                  .where(self.__class__.id == self.id)
                                  .values(**kwargs)
                                  .execution_options(synchronize_session="fetch"))
            await session.commit()
        return self

    @classmethod
    async def create(cls, **kwargs):
        async with db.session_ctx() as session:
            await session.add(cls(**kwargs))
            result = await session.commit()
        return result

    async def update(self, **kwargs):
        if "id" in kwargs.keys() or "created_at" in kwargs.keys():
            raise Exception("Cannot update id/created_at field")
        return await self.fill(**kwargs).save(update_fields=list(kwargs.keys()))

    async def delete(self):
        async with db.session_ctx() as session:
            await session.delete(self)
            await session.commit()

    @classmethod
    async def get_or_create(cls, defaults=None, **kwargs):
        if not kwargs:
            raise Exception("Param Kwargs Required")
        async with db.session_ctx() as session:
            instance = (await session.execute(select(cls).filter_by(**kwargs))).one_or_none()
            if instance:
                return instance, False
            else:
                params = {k: v for k, v in kwargs.items() if not isinstance(v, ClauseElement)}
                params.update(defaults or {})
                instance = cls(**params)
                try:
                    async with session.begin():
                        session.add(instance)
                        await session.flush([instance])
                except Exception:
                    # official documentation: https://docs.sqlalchemy.org/en/latest/orm/session_transaction.html
                    await session.rollback()
                    instance = (await session.execute(select(cls).filter_by(**kwargs).one_or_none())).scalars().first()
                    return instance, False
                else:
                    return instance, True

    @classmethod
    async def get(cls, pk):
        async with db.session_ctx() as session:
            results = await session.execute(select(cls).where(cls.id == pk))
            (result,) = results.one()
        return result

    @classmethod
    def filter(cls, *args, **kwargs) -> "Filter":
        return Filter(cls, *args, **kwargs)

    @classmethod
    async def first(cls, *args, **kwargs):
        return await Filter(cls, *args, **kwargs).first()

    @classmethod
    def join(cls, join_target: Union["BaseModel", AliasedClass], on):
        filter_ = Filter(cls)
        if isinstance(join_target, AliasedClass):
            filter_.join_models.add(inspect(join_target).class_)
        else:
            filter_.join_models.add(join_target)
        filter_.join_param.append((join_target, on))
        return filter_

    @classmethod
    async def select_func(cls, specific_func, field, **kwargs):
        async with db.session_ctx() as session:
            result = (await session.execute(
                select([specific_func(getattr(cls, field))]).select_from(cls).filter(
                    *(getattr(cls, k) == v for k, v in kwargs.items()))
            )).scalar()
        return result

    @classmethod
    async def total(cls, **kwargs):
        async with db.session_ctx() as session:
            total = (await session.execute(
                # (func.count(cls.id)).label('total')  rename for reference
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
        async with db.session_ctx() as session:
            data = (await session.execute(stmt)).scalars().all()
        return page_info, data

    class Config:
        """
        exclude, additional
        default order by id desc
        """
        exclude = []
        additional = []
        order_by = ["-id"]


class Filter:
    def __init__(self, model_cls, *args, **kwargs):
        self.query_model = model_cls
        self.join_models = set()  # joined model
        self.filter_args = [*args, ]
        self.filter_kwargs = [getattr(model_cls, k) == v for k, v in kwargs.items()]
        self.order_by_args = [
            getattr(model_cls, order_field.lstrip("-")).desc() if "-" in order_field else getattr(model_cls,
                                                                                                  order_field.lstrip(
                                                                                                      "+")).asc() for
            order_field in getattr(model_cls.Config, "order_by", [])]
        self.reverse_order_by_args = [
            getattr(model_cls, order_field.lstrip("-")).asc() if "-" in order_field else getattr(model_cls,
                                                                                                 order_field.lstrip(
                                                                                                     "+")).desc() for
            order_field in getattr(model_cls.Config, "order_by", [])]
        self.select_args = [model_cls]
        self.limit_ = None
        self.offset_ = None
        self.group_fields = None
        self.join_param = []  # [(table, on), ]
        self.having_param = None

    @classmethod
    def get_attr_of_related_models(cls, attr, related_models):
        """
        :return:
        """
        if isinstance(attr, str):
            temp = []
            for model in related_models:
                select_field = getattr(model, attr, None)
                if select_field:
                    temp.append(select_field)
            if not temp:
                raise Exception(f"Field {attr} doesn't exist in all related models: {', '.join(related_models)}")
            elif len(temp) > 1:
                raise (Exception(
                    f"Field {attr} is implicit in: {', '.join([f'{attr.class_}.{attr.key}' for attr in temp])}"))
            return temp[0]
        else:
            return attr

    def filter(self, *args, **kwargs) -> "Filter":
        """
        filter param
        :param args:
        :param kwargs:
        :return:
        """
        related_models = self.join_models
        related_models.add(self.query_model)
        self.filter_args.extend(args)
        self.filter_kwargs.extend([self.get_attr_of_related_models(k, related_models) == v for k, v in kwargs.items()])
        return self

    def group_by(self, *group_fields):
        self.group_fields = group_fields
        return self

    def order_by(self, *order_fields) -> "Filter":
        """
        order param
        :param order_fields:
        :return:
        """
        related_models = self.join_models
        related_models.add(self.query_model)
        for order_field in order_fields:
            if "-" in order_field:
                self.order_by_args.append(
                    self.get_attr_of_related_models(order_field.lstrip("-"), related_models).desc())
                self.reverse_order_by_args.append(
                    self.get_attr_of_related_models(order_field.lstrip("-"), related_models).asc())
            else:
                self.order_by_args.append(
                    self.get_attr_of_related_models(order_field.lstrip("+"), related_models).asc())
                self.reverse_order_by_args.append(
                    self.get_attr_of_related_models(order_field.lstrip("+"), related_models).desc())
        return self

    def having(self, *args):
        """

        :param args: having compare item
        :return:
        """
        self.having_param = args
        return self

    def values(self, *args) -> "Filter":
        """
        select values
        :param args:
        :return:
        """
        related_models = self.join_models
        related_models.add(self.query_model)
        self.select_args = set([self.get_attr_of_related_models(attr, related_models) for attr in args])
        return self

    def limit(self, limit: int) -> "Filter":
        self.limit_ = limit
        return self

    def offset(self, offset: int) -> "Filter":
        self.offset_ = offset
        return self

    async def result(self) -> AsyncScalarResult:
        stmt = select(*self.select_args).filter(*self.filter_args, *self.filter_kwargs)
        for table_model, on in self.join_param:
            if on:
                stmt = stmt.join(table_model, on)
            else:
                stmt = stmt.join(table_model)
        if self.group_fields:
            stmt = stmt.group_by(*self.group_fields)
        if self.having_param:
            stmt = stmt.having(*self.having_param)
        if self.order_by_args:
            stmt = stmt.order_by(*self.order_by_args)
        if self.limit_:
            stmt = stmt.limit_(self.limit_)
        if self.offset_:
            stmt = stmt.offset_(self.offset_)
        async with db.session_ctx() as session:
            results = (await session.execute(stmt)).scalars()
        return results

    async def all(self):
        return (await self.result()).all()

    async def first(self):
        return (await self.result()).first()

    async def last(self):
        self.order_by_args = self.reverse_order_by_args
        return (await self.result()).first()


class RelationObjectFilter(Filter):
    added_objects = []

    def __init__(self, parent_model_cls, model_cls, *args, **kwargs):
        if model_cls not in [relation.mapper.class_ for relation in inspect(parent_model_cls).relationships]:
            raise Exception(f"{model_cls} is not a relation object to {parent_model_cls}")
        self.parent_model = parent_model_cls
        super().__init__(model_cls, *args, **kwargs)

    def add(self, *args):
        assert all(isinstance(arg, self.query_model) for arg in args), f"Require instance of {self.query_model}"
        self.added_objects.extend(args)

    def join(self, join_target: Union["BaseModel", AliasedClass], on):
        if isinstance(join_target, AliasedClass):
            self.join_models.add(inspect(join_target).class_)
        else:
            self.join_models.add(join_target)
        self.join_param.append((join_target, on))
        return self
