from enum import Enum


class IntEnumMore(int, Enum):
    def __new__(cls, value, label):
        obj = int.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj

    @classmethod
    def choices(cls):
        return {item.value: item.label for item in cls}


class StrEnumMore(str, Enum):
    def __new__(cls, value, label):
        obj = str.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj

    @classmethod
    def choices(cls):
        return {item.value: item.label for item in cls}
