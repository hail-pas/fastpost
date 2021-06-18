from datetime import datetime

from sqlalchemy import Column, String, DateTime, func, ForeignKey, Integer
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref

from db import BaseModel


class User(BaseModel):
    __table_args__ = {'comment': "用户"}
    username = Column(comment="用户名", type_=String(150), default="")
    phone = Column(comment="手机号", type_=String(11), unique=True, nullable=False)
    password = Column(comment="密码", type_=String(100), nullable=False)
    last_login_at = Column(comment="最近登录时间", type_=DateTime)
    remark = Column(comment="备注", type_=String(200), default="")

    addresses = relationship(
        "Address", back_populates="user", cascade="all, delete, delete-orphan"
    )
    groups = relationship("Group", secondary="group_user", back_populates="users")
    profile = relationship("Profile", uselist=False, back_populates="user")

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
        exclude = ("password",)
        additional = ("from_last_login_days", "user_info")


class Address(BaseModel):
    __table_args__ = {'comment': "地址"}
    province = Column(comment="省/市", type_=String, nullable=False)
    city = Column(comment="区/县", type_=String, nullable=False)
    detail = Column(comment="详细地址", type_=String, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), comment="用户id")

    user = relationship("User", back_populates="addresses")


class Profile(BaseModel):
    __table_args__ = {'comment': "用户信息"}
    info = Column(comment="信息", type_=String, default="")
    user_id = Column(Integer, ForeignKey("user.id"), comment="用户id", unique=True)  # 一对一： 外键唯一约束

    user = relationship("User", back_populates="profile")


class Group(BaseModel):
    __table_args__ = {'comment': "分组"}
    label = Column(comment="组名称", type_=String(50), unique=True, nullable=False)
    remark = Column(comment="备注", type_=String(200), default="")

    permissions = relationship("Permission", secondary="group_permission", back_populates="groups")
    users = relationship("User", secondary="group_user", back_populates="groups")

    def __repr__(self):
        return self.name


class Permission(BaseModel):
    __table_args__ = {'comment': "权限"}
    label = Column(comment="权限名称", type_=String(50), unique=True, nullable=False)
    code = Column(comment="权限代码", type_=String(20), unique=True, nullable=False)
    remark = Column(comment="备注", type_=String(200), default="")

    groups = relationship("Group", secondary="group_permission", back_populates="permissions")

    def __repr__(self):
        return self.name


class GroupPermission(BaseModel):
    __table_args__ = {'comment': "分组权限关联表"}
    group_id = Column(Integer, ForeignKey("group.id"), comment="组id", nullable=False)
    permission_id = Column(Integer, ForeignKey("permission.id"), comment="用户id", nullable=False)


class GroupUser(BaseModel):
    __table_args__ = {'comment': "分组用户关联表"}
    group_id = Column(Integer, ForeignKey("group.id"), comment="组id", nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), comment="用户id", nullable=False)
