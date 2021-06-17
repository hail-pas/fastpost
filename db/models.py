from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, TIMESTAMP, DateTime, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from db import BaseModel


class User(BaseModel):
    __table_args__ = {'comment': "用户表"}
    username = Column(comment="用户名", type_=String(150), default="")
    phone = Column(comment="手机号", type_=String(11), unique=True, nullable=False)
    password = Column(comment="密码", type_=String(100), nullable=False)
    last_login_at = Column(comment="最近登录时间", type_=DateTime)
    remark = Column(comment="备注", type_=String(200), default="")

    def __repr__(self):
        return f"{self.username}-{self.phone}"

    @hybrid_property
    def from_last_login_days(self):
        if not self.last_login_at:
            return None
        return datetime.now().day - self.last_login_at.day

    @from_last_login_days.expression
    def from_last_login_days(self):
        return datetime.now().day - func.day(self.last_login_at)

    @property
    def user_info(self):
        return f"{self.username}-{self.phone}"

    class Config:
        excludes = ("password",)
        additional = ("from_last_login_days", "user_info")


class Group(BaseModel):
    label = Column(comment="组名称", type_=String(50), unique=True, nullable=False)
    remark = Column(comment="备注", type_=String(200), default="")

    def __repr__(self):
        return self.name


class Permission(BaseModel):
    label = Column(comment="权限名称", type_=String(50), unique=True, nullable=False)
    code = Column(comment="权限代码", type_=String(20), unique=True, nullable=False)
    remark = Column(comment="备注", type_=String(200), default="")

    def __repr__(self):
        return self.name


class GroupPermission(BaseModel):
    pass


class GroupUser(BaseModel):
    pass
