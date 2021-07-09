from common.types import IntEnumMore, StrEnumMore


class GeneralStatus(IntEnumMore):
    on = (0, "开启")
    off = (1, "关闭")
    not_confirm = (2, "待确认")


class EmissionLevel(StrEnumMore):
    guo1 = ("guo1", "国一")
    guo2 = ("guo2", "国二")
    guo3 = ("guo3", "国三")
    guo4 = ("guo4", "国四")
    guo5 = ("guo5", "国五")
    guo6 = ("guo6", "国六")
