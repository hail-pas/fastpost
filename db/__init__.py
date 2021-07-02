import re
import abc
import uuid
from typing import List, Type, Union, TypeVar, Optional
from asyncio import sleep, current_task
from datetime import datetime
from contextlib import asynccontextmanager

import sqlalchemy
from pydantic import BaseConfig, create_model
from sqlalchemy import func, delete, insert, select, update, inspect
from sqlalchemy.orm import (ColumnProperty, DeclarativeMeta,
                            RelationshipProperty, joinedload, sessionmaker,
                            declared_attr, declarative_base)
from sqlalchemy.sql import ClauseElement
from pydantic.fields import FieldInfo, ModelField
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.ext.asyncio import (AsyncSession, create_async_engine,
                                    async_scoped_session)
from sqlalchemy.sql.operators import is_
from sqlalchemy.orm.clsregistry import _ModuleMarker
from sqlalchemy.ext.asyncio.result import AsyncScalarResult

from fastpost.types import Pager
from fastpost.response import generate_page_info
from fastpost.settings import get_settings


def create_engine():
    return create_async_engine(
        get_settings().POSTGRES_DATABASE_URL_ASYNC, echo=get_settings().DEBUG, pool_timeout=30, pool_pre_ping=True,
        max_overflow=0, pool_size=80 // get_settings().WORKERS, pool_recycle=3600, future=True,
    )


# fmt: off
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
    async def session_ctx(self) -> AsyncSession:
        db_session = async_scoped_session(self.session_maker, current_task)
        try:
            yield db_session  # type: AsyncSession
        finally:
            await db_session.close()

    def get_model_by_table(self, table):
        for c in self.Model.registry._class_registry.values():
            if isinstance(c, _ModuleMarker):
                continue
            if inspect(c).local_table == table:
                return c


# fmt: on


db = SQLAlchemy()


class BaseModelMeta(DeclarativeMeta, abc.ABCMeta):
    PyModel = TypeVar('PyModel', bound='BaseModel')
    common_column = ["id", "created_at", "updated_at"]

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
                "id": ModelField(name="id", type_=int, default=..., required=True,
                                 field_info=FieldInfo(default=..., title="主键", description="唯一标示"),
                                 model_config=Config, class_validators=None)
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
                        kwargs[column_name] = ModelField(name=column_name, type_=python_type, default=None,
                                                         required=bool(default),
                                                         field_info=FieldInfo(default=None,
                                                                              title=attr.columns[0].comment,
                                                                              description=attr.columns[0].comment),
                                                         model_config=Config, class_validators=None)
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
                    additional_attr = getattr(model, additional, None)
                    if additional_attr:
                        title = ""
                        attr_doc = additional_attr.fget.__doc__
                        if attr_doc:
                            title = attr_doc.split("\n")[0] or attr_doc.split("\n")[1]
                        kwargs[additional] = ModelField(name=additional,
                                                        type_=additional_attr.fget.__annotations__.get("return"),
                                                        required=False,
                                                        field_info=FieldInfo(default=None, title=title,
                                                                             description=title),
                                                        model_config=Config, class_validators=None)
            kwargs["updated_at"] = ModelField(name="updated_at", type_=datetime, default=None, required=True,
                                              field_info=FieldInfo(default=None, title="更新时间",
                                                                   description="更新时间"),
                                              model_config=Config, class_validators=None)
            kwargs["created_at"] = ModelField(name="created_at", type_=datetime, default=None, required=True,
                                              field_info=FieldInfo(default=None, title="创建时间",
                                                                   description="创建时间"),
                                              model_config=Config, class_validators=None)
            temp = create_model(f"{model.__name__}RespModel{str(uuid.uuid1())[:8]}",
                                __config__=Config)
            temp.__fields__ = kwargs
            return temp

        return generate_response_model(cls, 0)

    @property
    def create_schema(cls):
        kwargs = {}
        validators = {}

        class Config(BaseConfig):
            anystr_strip_whitespace = True

        for attr in inspect(cls).attrs:
            if isinstance(attr, ColumnProperty):
                if attr.columns:
                    column_name = attr.key
                    if column_name in cls.common_column or column_name.endswith("_id"):
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
                    if attr.direction.name == "MANYTOMANY":
                        kwargs[attr.key] = (Optional[List[int]], None)
                    elif attr.direction.name == "ONETOMANY":
                        kwargs[attr.key] = (Optional[List[int]], None)
                    elif attr.direction.name == "MANYTOONE":
                        kwargs[attr.key] = (Optional[int], None)
        return create_model(f"{cls.__name__}CreateSchema{str(uuid.uuid1())[:8]}", __validators__=validators,
                            # __module__=f"db.{str(uuid.uuid1())[:8]}",
                            __config__=Config, **kwargs)

    @property
    def update_schema(cls):
        kwargs = {}
        validators = {}

        class Config(BaseConfig):
            anystr_strip_whitespace = True

        for attr in inspect(cls).attrs:
            if isinstance(attr, ColumnProperty):
                if attr.columns:
                    column_name = attr.key
                    if column_name in cls.common_column or column_name.endswith("_id"):
                        continue
                    column = attr.columns[0]
                    python_type: Optional[type] = None
                    if hasattr(column.type, "impl"):
                        if hasattr(column.type.impl, "python_type"):
                            python_type = column.type.impl.python_type
                    elif hasattr(column.type, "python_type"):
                        python_type = column.type.python_type
                    assert python_type, f"Could not infer python_type for {column}"
                    kwargs[column_name] = (Optional[python_type], None)
            elif isinstance(attr, RelationshipProperty):

                if not attr.uselist:
                    kwargs[attr.key] = (Optional[int], None)
                else:
                    if attr.direction.name == "MANYTOMANY":
                        kwargs[attr.key] = (Optional[List[int]], None)
                    elif attr.direction.name == "ONETOMANY":
                        kwargs[attr.key] = (Optional[List[int]], None)
                    elif attr.direction.name == "MANYTOONE":
                        kwargs[attr.key] = (Optional[int], None)
        return create_model(f"{cls.__name__}UpdateSchema{str(uuid.uuid1())[:8]}", __validators__=validators,
                            # __module__=f"db.{str(uuid.uuid1())[:8]}",
                            __config__=Config, **kwargs)

    @property
    def create_filter_query(cls):
        kwargs = {}
        for attr in inspect(cls).attrs:
            if isinstance(attr, ColumnProperty):
                if attr.columns:
                    column_name = attr.key
                    if column_name in cls.common_column or column_name.endswith("_id"):
                        continue
                    column = attr.columns[0]
                    python_type: Optional[type] = None
                    if hasattr(column.type, "impl"):
                        if hasattr(column.type.impl, "python_type"):
                            python_type = column.type.impl.python_type
                    elif hasattr(column.type, "python_type"):
                        python_type = column.type.python_type
                    assert python_type, f"Could not infer python_type for {column}"
                    kwargs[column_name] = Optional[python_type]
            elif isinstance(attr, RelationshipProperty):
                if not attr.uselist:
                    kwargs[attr.key] = Optional[int]
                else:
                    if attr.direction.name == "MANYTOMANY":
                        kwargs[attr.key] = Optional[List[int]]
                    elif attr.direction.name == "ONETOMANY":
                        kwargs[attr.key] = Optional[List[int]]
                    elif attr.direction.name == "MANYTOONE":
                        kwargs[attr.key] = Optional[int]
            return kwargs


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
        if item in [relation.key for relation in inspect(type(self)).relationships] or item in [f"{relation.key}_proxy"
                                                                                                for relation in inspect(
                type(self)).relationships]:
            relation = getattr(inspect(type(self)).attrs, item)
            many2many = many2one = None
            if relation.direction.name == "MANYTOMANY":
                many2many = RelationObjectFilter(type(self), relation.mapper.class_).join(
                    db.get_model_by_table(relation.secondary),
                    getattr(relation.mapper.class_, list(relation.local_columns)[0].key) == getattr(
                        db.get_model_by_table(relation.secondary),
                        relation.local_remote_pairs[0][1].key)).filter(
                    getattr(db.get_model_by_table(relation.secondary),
                            relation.local_remote_pairs[0][1].key) == self.to_dict().get(
                        relation.local_remote_pairs[0][0].key))
            else:
                many2one = RelationObjectFilter(type(self), relation.mapper.class_, **{
                    f"{relation.local_remote_pairs[0][1].key}": self.to_dict().get(
                        relation.local_remote_pairs[0][0].key)})
            if item.endswith("_proxy"):
                if relation.direction.name == "MANYTOMANY":
                    return many2many
                else:
                    return many2one
            else:
                if not relation.uselist:
                    return many2one.first()
                if relation.direction.name == "ONETOMANY":
                    return many2one.all()
                if relation.direction.name == "MANYTOONE":
                    return many2one.first()
                if relation.direction.name == "MANYTOMANY":
                    return many2many.all()
        return super().__getattribute__(item)

    def __setattr__(self, key, value):
        if key == "id":
            raise Exception("Cannot setattr of id")
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
            o2m_relation_kwargs_list = []
            m2m_relation_kwargs = {
                "add": [],
                "remove": []
            }
            for key in update_fields:
                if key not in self_dict.keys():
                    if "proxy" in key and key.split("_")[0] in [relation.key for relation in
                                                                inspect(type(self)).relationships]:
                        relation_object_filter = getattr(self, key)  # type: RelationObjectFilter
                        relation = relation_object_filter.relation
                        relation_kwargs_list_temp = []
                        if relation.direction.name == "ONETOMANY":
                            self_related_value = getattr(self, relation.local_remote_pairs[0][0].key)
                            remote_related_field = getattr(relation.mapper.class_,
                                                           relation.local_remote_pairs[0][1].key)
                            remote_related_field_key = relation.local_remote_pairs[0][1].key
                            # add
                            for o in relation_object_filter.added_objects:
                                relation_kwargs = {
                                    "model": relation.mapper.class_,
                                    "where": [
                                        is_(remote_related_field, None),
                                        relation.mapper.class_.id == o.id, ],
                                    "values": {
                                        remote_related_field_key: self_related_value
                                    }
                                }
                                relation_kwargs_list_temp.append(relation_kwargs)
                            # remove
                            for o in relation_object_filter.removed_objects:
                                relation_kwargs = {
                                    "model": relation.mapper.class_,
                                    "where": [relation.mapper.class_.id == o.id,
                                              remote_related_field == self_related_value],
                                    "values": {
                                        remote_related_field_key: None
                                    }
                                }
                                relation_kwargs_list_temp.append(relation_kwargs)
                            o2m_relation_kwargs_list.extend(relation_kwargs_list_temp)
                        elif relation.direction.name == "MANYTOONE":
                            # only need change self
                            if relation_object_filter.change_to_object:
                                kwargs[relation.local_remote_pairs[0][0].key] = getattr(
                                    relation_object_filter.change_to_object, relation.local_remote_pairs[0][1].key)
                            elif relation_object_filter.removed_objects:
                                existed_value = getattr(self, relation.local_remote_pairs[0][0].key)
                                remove_target_value = getattr(
                                    relation_object_filter.removed_objects[0], relation.local_remote_pairs[0][1])
                                if existed_value != remove_target_value:
                                    raise Exception(
                                        f"""Current object {relation.mapper.class_}-{existed_value} doesnt consist """
                                        """with the object {relation.mapper.class_}-{remove_target_value} which """
                                        """waiting for removing""")
                                kwargs[relation.local_remote_pairs[0][0].key] = None
                            else:
                                raise Exception("Must use change_to first to specify the target object")
                        elif relation.direction.name == "MANYTOMANY":
                            # add
                            secondary_model = db.get_model_by_table(relation.secondary)
                            relation_kwargs = {
                                "model": secondary_model,
                            }
                            self_related_value = getattr(self, relation.local_remote_pairs[0][0].key)
                            self2secondary_key = relation.local_remote_pairs[0][1].key
                            remote_key = relation.local_remote_pairs[1][0].key
                            remote2secondary_key = relation.local_remote_pairs[1][1].key
                            for o in relation_object_filter.added_objects:
                                relation_kwargs["values"] = {
                                    self2secondary_key: self_related_value,
                                    remote2secondary_key: getattr(o, remote_key)
                                }
                                m2m_relation_kwargs["add"].append(relation_kwargs)
                            # remove
                            for o in relation_object_filter.removed_objects:
                                relation_kwargs["where"] = [
                                    self2secondary_key == self_related_value,
                                    remote2secondary_key == getattr(o, remote_key),
                                ]
                                m2m_relation_kwargs["remove"].append(relation_kwargs)
                        else:
                            raise NotImplementedError
                    else:
                        raise Exception(f"Field {key} doesn't exist")
                v = self_dict.get(key)
                kwargs[key] = v
        async with db.session_ctx() as session:
            try:
                # update self
                await session.execute(update(self.__class__)
                                      .where(self.__class__.id == self.id)
                                      .values(**kwargs)
                                      .execution_options(synchronize_session="fetch"))
                # update o2m relationship
                for relation_kwargs in o2m_relation_kwargs_list:
                    await session.execute(
                        update(relation_kwargs.get("model")).where(*relation_kwargs.get("where")).values(
                            **relation_kwargs.get("values")))
                # m2m add
                for relation_kwargs in m2m_relation_kwargs["add"]:
                    await session.execute(
                        insert(relation_kwargs.get("model")).values(
                            **relation_kwargs.get("values")))
                # m2m remove
                for relation_kwargs in m2m_relation_kwargs["remove"]:
                    await session.execute(
                        delete(relation_kwargs.get("model")).where(*relation_kwargs.get("where")))
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
        return self

    @classmethod
    async def create(cls, **kwargs):
        one2many_kwargs_list = []
        many2many_kwargs_list = []
        for k, v in kwargs.items():
            attr = inspect(cls).attrs.get(k)
            if not attr:
                raise Exception(f"{k} doesnt exist in model {cls}")
            if isinstance(attr, RelationshipProperty):
                if attr.direction.name == "MANYTOONE":
                    if isinstance(v, attr.mapper.class_):
                        kwargs[attr.local_remote_pairs[0][0].key] = getattr(v, attr.local_remote_pairs[0][1].key)
                        del kwargs[k]
                    else:
                        raise Exception(f"the {k} need instance of {attr.mapper.class_}")
                elif attr.direction.name == "ONETOMANY":
                    remote_related_field = getattr(attr.mapper.class_,
                                                   attr.local_remote_pairs[0][1].key)
                    remote_related_field_key = attr.local_remote_pairs[0][1].key
                    for o in v:
                        if not isinstance(o, attr.mapper.class_):
                            raise Exception(f"the {k} need instance of {attr.mapper.class_}")
                        relation_kwargs = {
                            "model": attr.mapper.class_,
                            "where": [
                                is_(remote_related_field, None),
                                attr.mapper.class_.id == o.id, ],
                            "value_key": remote_related_field_key
                        }
                        one2many_kwargs_list.append(relation_kwargs)
                elif attr.direction.name == "MANYTOMANY":
                    secondary_model = db.get_model_by_table(attr.secondary)
                    relation_kwargs = {
                        "model": secondary_model,
                    }
                    remote_key = attr.local_remote_pairs[1][0].key
                    remote2secondary_key = attr.local_remote_pairs[1][1].key
                    for o in v:
                        if not isinstance(o, attr.mapper.class_):
                            raise Exception(f"the {k} need instance of {attr.mapper.class_}")
                        relation_kwargs["value_key"] = attr.local_remote_pairs[0][1].key
                        relation_kwargs["values"] = {
                            remote2secondary_key: getattr(o, remote_key)
                        }
                        many2many_kwargs_list.append(relation_kwargs)

        async with db.session_ctx() as session:
            try:
                result = await session.execute(
                    insert(cls).values(**kwargs).execution_options(synchronize_session="fetch"))

                created_pk = result.inserted_primary_key[0]

                for relation_kwargs in one2many_kwargs_list:
                    await session.execute(
                        update(relation_kwargs.get("model")).where(*relation_kwargs.get("where")).values(
                            **{relation_kwargs.get("value_key"): created_pk}))
                # m2m add
                for relation_kwargs in many2many_kwargs_list:
                    await session.execute(
                        insert(relation_kwargs.get("model")).values(**relation_kwargs.get("values"),
                                                                    **{relation_kwargs.get("value_key"): created_pk}))

                await session.commit()
                return await cls.get(created_pk)
            except Exception as e:
                await session.rollback()
                raise e

    async def update(self, **kwargs):
        if "id" in kwargs.keys() or "created_at" in kwargs.keys():
            raise Exception("Cannot update id/created_at field")
        return await self.fill(**kwargs).save(update_fields=list(kwargs.keys()))

    async def delete(self):
        await self.delete_with_pk(self.id)
        self.__del__()

    @classmethod
    async def delete_with_pk(cls, pk: int):
        stmt = delete(cls).where(cls.id == int(pk))
        async with db.session_ctx() as session:
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def update_with_pk(cls, pk: int, values: dict, one2many: List = None, many2many: List = None):
        async with db.session_ctx() as session:
            await session.execute(
                update(cls).where(cls.id == int(pk)).values(**values).execution_options(synchronize_session="fetch"))

            if one2many:
                for related_model, related_pk, related_field in one2many:
                    pass

            if many2many:
                for related_model, related_left_field, related_right_field in many2many:
                    pass

            await session.commit()
            return await cls.get(pk)

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
            results = await session.execute(select(cls).where(cls.id == int(pk)))
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
        order_by_args = [
            getattr(cls, order_field.lstrip("-")).desc() if "-" in order_field else getattr(cls,
                                                                                            order_field.lstrip(
                                                                                                "+")).asc() for
            order_field in getattr(cls.Config, "order_by", ["-id"])]
        if join_loads:
            stmt = select(cls).options(
                joinedload(*[getattr(cls, attr) for attr in join_loads])).filter(
                *[getattr(cls, k) == v for k, v in kwargs.items()]).order_by(*order_by_args).offset(pager.offset).limit(
                pager.limit)
        else:
            stmt = select(cls).filter(
                *[getattr(cls, k) == v for k, v in kwargs.items()]).order_by(*order_by_args).offset(pager.offset).limit(
                pager.limit)
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
            order_field in getattr(model_cls.Config, "order_by", ["-id"])]
        self.reverse_order_by_args = [
            getattr(model_cls, order_field.lstrip("-")).asc() if "-" in order_field else getattr(model_cls,
                                                                                                 order_field.lstrip(
                                                                                                     "+")).desc() for
            order_field in getattr(model_cls.Config, "order_by", ["-id"])]
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
    removed_objects = []
    change_to_object = None
    relation: RelationshipProperty = None

    def __init__(self, parent_model_cls, model_cls, *args, **kwargs):
        for relation in inspect(parent_model_cls).relationships:
            if model_cls == relation.mapper.class_:
                self.relation = relation
        if not self.relation:
            raise Exception(f"{model_cls} is not a relation object to {parent_model_cls}")
        self.parent_model = parent_model_cls
        super().__init__(model_cls, *args, **kwargs)

    def join(self, join_target: Union["BaseModel", AliasedClass], on):
        if isinstance(join_target, AliasedClass):
            self.join_models.add(inspect(join_target).class_)
        else:
            self.join_models.add(join_target)
        self.join_param.append((join_target, on))
        return self

    def add(self, *args):
        """
        新增
        :param args:
        :return:
        """
        if self.relation.direction.name == "MANYTOONE":
            raise Exception("Cannot add objetc at MANY side in MANYTOONE relationship， maybe the change_to")
        assert all(isinstance(arg, self.query_model) for arg in args), f"Require instance of {self.query_model}"
        self.added_objects.extend(args)

    def remove(self, *args):
        """
        解除
        :param args:
        :return:
        """
        assert all(isinstance(arg, self.query_model) for arg in args), f"Require instance of {self.query_model}"
        self.removed_objects.extend(args)
        if self.relation.direction.name != "MANYTOONE":
            assert len(
                self.removed_objects) == 1, "MANY side in MANYTOONE relationship must have only one related object "

    def change_to(self, arg):
        """
        change the one of many2one
        :param arg:
        :return:
        """
        if self.relation.direction.name != "MANYTOONE":
            raise Exception("Cannot only use change_to at MANY side in MANYTOONE relationship")
        assert isinstance(arg, self.query_model), f"Require instance of {self.query_model}"
        self.change_to_object = arg
