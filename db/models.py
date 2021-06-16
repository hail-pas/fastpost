from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from db import BaseModel, db


class User(db.Model, BaseModel):
    username = Column(comment="用户名", type_=String(150), default="")
    phone = Column(comment="手机号", type_=String(11), unique=True, nullable=False)
    password = Column(comment="密码", type_=String(100), nullable=False)
    remark = Column(comment="备注", type_=String(200), default="")

    def __repr__(self):
        return f"{self.username}-{self.phone}"


class Group(db.Model, BaseModel):
    label = Column(comment="组名称", type_=String(50), unique=True, nullable=False)
    remark = Column(comment="备注", type_=String(200), default="")

    def __repr__(self):
        return self.name


class Permission(db.Model, BaseModel):
    label = Column(comment="权限名称", type_=String(50), unique=True, nullable=False)
    code = Column(comment="权限代码", type_=String(20), unique=True, nullable=False)
    remark = Column(comment="备注", type_=String(200), default="")

    def __repr__(self):
        return self.name


class GroupPermission(db.Model, BaseModel):
    pass


class GroupUser(db.Model, BaseModel):
    pass
