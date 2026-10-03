"""
图谱规范值对象 — 描述知识图谱的结构

为什么做：知识图谱的节点/边结构需要在领域层被显式描述与校验，
        避免基础设施层直接暴露存储细节给上层。
实现方法：GraphSpec 持有结构标识，validate()/to_dict()/from_dict()
        负责自校验与序列化契约。
层&依赖：domain 层（值对象），依赖 shared
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
