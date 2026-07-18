"""
执行模式值对象 — 定义 AI 的对话/探索模式

TODO: 填充业务方法后移除 __init__ 中字段定义

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class ModeConfig(ValueObject):
    """执行模式配置值对象"""

    def __init__(self, name: str = "explore") -> None:
        self._name = name

    def is_explore(self) -> bool:
        return self._name == "explore"

    def is_chat(self) -> bool:
        return self._name == "chat"

    def __str__(self) -> str:
        return self._name


class ExecutionMode(ValueObject):
    """执行模式值对象 — 定义 AI 的对话/探索模式"""

    def __init__(self, value: str = "") -> None:
        self._value = value
