"""
图谱规范值对象 — 描述知识图谱的结构

TODO: 填充业务方法后移除 __init__ 中字段定义

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class GraphSpec(ValueObject):
    """图谱规范值对象 — 描述知识图谱的结构"""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def validate(self) -> None:
        """TODO: GraphSpec.validate"""
        pass

    def to_dict(self) -> None:
        """TODO: GraphSpec.to_dict"""
        pass

    def from_dict(self) -> None:
        """TODO: GraphSpec.from_dict"""
        pass
