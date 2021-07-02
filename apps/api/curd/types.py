from enum import Enum


class ComparisonOperator(str, Enum):
    eq = "EQ"
    like = "LIKE"
    starts_with = "STARTS_WITH"
    in_ = "IN"
    gt = "GT"
    gte = "GE"
    lt = "LT"
    lte = "LE"


class LogicalOperator(str, Enum):
    and_ = "AND"


class Ordering(str, Enum):
    asc = "ASC"
    desc = "DESC"
