"""ValueObject — 值对象基类

为什么做：DDD 中值对象没有唯一标识，仅靠属性值区分。两个值对象的所有属性相同则视为相等。
典型用途：金额、地址、日期范围、定价配置等。

实现方法：ABC 基类，__eq__ 基于 __dict__ 比较，__hash__ 基于排序后的属性元组。
使用方式：@dataclass(frozen=True) class Foo(ValueObject)

层&依赖：shared.kernel 层，零依赖
"""

from abc import ABC
from typing import Any


class ValueObject(ABC):
    """值对象基类 — 不可变，按所有属性值相等

    使用方式：
        @dataclass(frozen=True)
        class Address(ValueObject):
            city: str
            street: str
    """

    def __eq__(self, other: Any) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)
