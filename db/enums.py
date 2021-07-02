from enum import IntEnum


class EnumMixin:
    @classmethod
    def choices(cls):
        raise NotImplementedError


class EmissionLevel(EnumMixin, IntEnum):
    level_1 = 1
    level_2 = 2
    level_3 = 3

    @classmethod
    def choices(cls):
        return {cls.level_1: "国一", cls.level_2: "国二", cls.level_3: "国三"}
