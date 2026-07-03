"""实体基类 — 有唯一标识，按 ID 相等

所有聚合内的实体必须继承此类。id 在首次赋值后不应修改。

层&依赖：shared.kernel 层，零依赖
"""

from abc import ABC
from typing import Any, Optional
from uuid import uuid4


class Entity(ABC):
    """实体基类 — 有唯一标识，按 ID 相等

    所有聚合内的实体必须继承此类。
    id 在首次赋值后不应修改。
    """

    def __init__(self, id: Optional[str] = None) -> None:
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
