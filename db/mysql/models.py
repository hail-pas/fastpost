from typing import Optional

from tortoise import fields

from db.mysql import BaseModel, enums
from common.utils import datetime_now


class Config(BaseModel):
    label = fields.CharField(max_length=200)
    key = fields.CharField(max_length=100, unique=True)
    value = fields.JSONField()
    safe = fields.BooleanField(default=False, description="是否可返回")
    # noinspection PyTypeChecker
    status = fields.IntEnumField(enums.GeneralStatus, description="状态", default=enums.GeneralStatus.on)

    def status_display(self) -> str:
        return self._meta.fields_map.get("status").enum_type.choices().get(self.status)

    class PydanticMeta:
        exclude = ("safe", "status")
        computed = ("status_display",)

    class Meta:
        table_description = "在线参数配置"


class User(BaseModel):
    username = fields.CharField(max_length=50, description="用户名称", unique=True)
    phone = fields.CharField(max_length=11, description="手机号", unique=True)
    password = fields.CharField(max_length=128, description="密码")
    last_login_at = fields.DatetimeField(null=True, description="最近一次登录时间")
    remark = fields.CharField(max_length=256, default="", description="备注")
    # noinspection PyTypeChecker
    status = fields.IntEnumField(enum_type=enums.GeneralStatus, description="状态", default=enums.GeneralStatus.on)

    profile: fields.ReverseRelation["Profile"]
    addresses: fields.ReverseRelation["Address"]
    groups: fields.ReverseRelation["Group"]

    def __str__(self):
        return f"{self.username}-{self.phone}"

    def status_display(self) -> str:
        return self._meta.fields_map.get("status").enum_type.choices().get(self.status)

    def from_last_login_days(self) -> Optional[int]:
        """
        距上一次登录天数
        :return:
        """
        if not self.last_login_at:
            return None
        return (datetime_now() - self.last_login_at).days

    class Meta:
        table_description = "用户"
        ordering = ["-id"]

    class PydanticMeta:
        computed = ("from_last_login_days", "status_display")


class Address(BaseModel):
    province = fields.CharField(max_length=256, description="省/市")
    city = fields.CharField(max_length=256, description="城市")
    detail = fields.CharField(max_length=256, description="详情")
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("models.User", related_name="addresses")

    class Meta:
        table_description = "地址"


class Profile(BaseModel):
    info = fields.CharField(max_length=256, default="", description="信息")
    user: fields.OneToOneRelation[User] = fields.OneToOneField("models.User", related_name="profile")

    class Meta:
        table_description = "用户信息"


class Permission(BaseModel):
    label = fields.CharField(max_length=50, unique=True, description="权限名称")
    code = fields.CharField(max_length=20, unique=True, description="权限代码")
    remark = fields.CharField(max_length=256, default="", description="备注")

    groups: fields.ReverseRelation["Group"]

    def __str__(self):
        return self.label

    class Meta:
        table_description = "权限"


class Group(BaseModel):
    label = fields.CharField(max_length=50, unique=True, description="组名")
    remark = fields.CharField(max_length=256, default="", description="备注")
    permissions: fields.ManyToManyRelation[Permission] = fields.ManyToManyField(
        "models.Permission", related_name="groups"
    )
    users: fields.ManyToManyRelation[User] = fields.ManyToManyField("models.User", related_name="groups")

    def __str__(self):
        return self.label

    class Meta:
        table_description = "分组"
