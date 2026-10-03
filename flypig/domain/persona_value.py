"""
角色值对象 — AI 助手的角色设定

为什么做：同一个 Agent 需要按场景切换人格（开发者/分析师/教师），把角色描述收敛成
        值对象，避免提示词散落在各 service 里拼接。
实现方法：Persona 持有角色标识，提供 to_system_message()/describe() 生成提示词片段。
层&依赖：domain 层（值对象），依赖 shared
"""

from flypig.shared.base import ValueObject


class Persona(ValueObject):
    """角色值对象 — AI 助手的角色设定"""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def to_system_message(self) -> None:
        """TODO: Persona.to_system_message"""
        pass

    def describe(self) -> None:
        """TODO: Persona.describe"""
        pass
