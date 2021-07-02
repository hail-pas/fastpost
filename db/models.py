from typing import Optional
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from db import BaseModel


class User(BaseModel):
    __table_args__ = {"comment": "用户"}
    username = Column(comment="用户名", type_=String(150), default="")
    phone = Column(comment="手机号", type_=String(11), unique=True, nullable=False)
    password = Column(comment="密码", type_=String(100), nullable=False)
    last_login_at = Column(comment="最近登录时间", type_=DateTime)
    remark = Column(comment="备注", type_=String(200), default="")

    # 自关联
    # parent_id = Column(Integer, ForeignKey('user.id'), comment="父级ID")
    # parent = relationship('User', back_populates="children", remote_side=[id])
    # children = relationship("User", back_populates="parent", remote_side=[parent_id])

    addresses = relationship("Address", back_populates="user", cascade="all, delete, delete-orphan")
    groups = relationship("Group", secondary="group_user", back_populates="users")
    profile = relationship("Profile", uselist=False, back_populates="user")

    def __repr__(self):
        return f"{self.username}-{self.phone}"

    @hybrid_property
    def from_last_login_days(self) -> Optional[int]:
        """
        距上一次登录天数
        :return:
        """
        if not self.last_login_at:
            return None
        return (datetime.now() - self.last_login_at).days

    @from_last_login_days.expression
    def from_last_login_days(self):
        return func.days(datetime.now() - self.last_login_at)

    @property
    def user_info(self) -> str:
        """
        用户信息
        :return:
        """
        return f"{self.username}-{self.phone}"

    class Config:
        exclude = ("password",)
        additional = ("from_last_login_days", "user_info")


class Address(BaseModel):
    __table_args__ = {"comment": "地址"}
    province = Column(comment="省/市", type_=String, nullable=False)
    city = Column(comment="区/县", type_=String, nullable=False)
    detail = Column(comment="详细地址", type_=String, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), comment="用户id")

    user = relationship("User", back_populates="addresses")

    # need use await to obtain related object, not implement
    # @property
    # def user_name(self) -> Optional[str]:
    #     return self.user.username

    class Config:
        additional = ("user_name",)


class Profile(BaseModel):
    __table_args__ = {"comment": "用户信息"}
    info = Column(comment="信息", type_=String, default="")
    user_id = Column(Integer, ForeignKey("user.id"), comment="用户id", unique=True)  # 一对一： 外键唯一约束

    user = relationship("User", back_populates="profile")


class Group(BaseModel):
    __table_args__ = {"comment": "分组"}
    label = Column(comment="组名称", type_=String(50), unique=True, nullable=False)
    remark = Column(comment="备注", type_=String(200), default="")

    permissions = relationship("Permission", secondary="group_permission", back_populates="groups")
    users = relationship("User", secondary="group_user", back_populates="groups")

    def __repr__(self):
        return self.label


class Permission(BaseModel):
    __table_args__ = {"comment": "权限"}
    label = Column(comment="权限名称", type_=String(50), unique=True, nullable=False)
    code = Column(comment="权限代码", type_=String(20), unique=True, nullable=False)
    remark = Column(comment="备注", type_=String(200), default="")

    groups = relationship("Group", secondary="group_permission", back_populates="permissions")

    def __repr__(self):
        return self.name


class GroupPermission(BaseModel):
    __table_args__ = {"comment": "分组权限关联表"}
    group_id = Column(Integer, ForeignKey("group.id"), comment="组id", nullable=False)
    permission_id = Column(Integer, ForeignKey("permission.id"), comment="用户id", nullable=False)


class GroupUser(BaseModel):
    __table_args__ = {"comment": "分组用户关联表"}
    group_id = Column(Integer, ForeignKey("group.id"), comment="组id", nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), comment="用户id", nullable=False)
