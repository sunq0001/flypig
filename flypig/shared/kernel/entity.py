"""Entity — 实体基类

为什么做：DDD 中需要区分有唯一标识的对象（实体）和仅靠属性值区分的对象（值对象）。
实体按 ID 判等，即使其他属性完全一样，ID 不同就是不同对象。

实现方法：ABC 基类，构造时自动生成 UUID。__eq__ 基于 ID 比较，__hash__ 返回 hash(ID)。
id 在首次赋值后不应修改。

层&依赖：shared.kernel 层，零依赖
"""

from abc import ABC
from typing import Any
from uuid import uuid4


class Entity(ABC):
    """实体基类 — 有唯一标识，按 ID 相等

    所有聚合内的实体必须继承此类。
    id 在首次赋值后不应修改。
    """

    def __init__(self, id: str | None = None) -> None:
        self._id: str = id or str(uuid4())

    @property
    def id(self) -> str:
        return self._id

    def __eq__(self, other: Any) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
