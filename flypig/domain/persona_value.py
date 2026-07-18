"""
角色值对象 — AI 助手的角色设定

TODO: 填充业务方法后移除 __init__ 中字段定义

层&依赖：domain 层，依赖 shared
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
