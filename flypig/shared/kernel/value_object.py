"""值对象基类 — 不可变，按所有属性值相等

使用 @dataclass(frozen=True) 继承此类。equals 基于所有属性值，不是 ID。

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
