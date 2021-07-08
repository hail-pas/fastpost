from enum import Enum, IntEnum


class EnumMixin:
    @classmethod
    def choices(cls):
        raise NotImplementedError


class GeneralStatus(EnumMixin, IntEnum):
    on = 0
    off = 1
    not_confirm = 2

    @classmethod
    def choices(cls):
        return {cls.on: "开启", cls.off: "关闭", cls.not_confirm: "待确认"}


class EmissionLevel(EnumMixin, str, Enum):
    guo1 = "guo1"
    guo2 = "guo2"
    guo3 = "guo3"
    guo4 = "guo4"
    guo5 = "guo5"
    guo6 = "guo6"

    @classmethod
    def choices(cls):
        return {cls.guo1: "国一", cls.guo2: "国二", cls.guo3: "国三", cls.guo4: "国四", cls.guo5: "国五", cls.guo6: "国六"}
