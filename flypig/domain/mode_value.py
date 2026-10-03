"""
执行模式值对象 — 定义 AI 的对话/探索模式

为什么做：模式决定 AI 能否直接改文件、跑命令，领域层需要统一回答「该模式是否危险」，
        避免路由层和 UI 各自硬编码模式名单，产生判断分歧。
实现方法：ModeConfig 封装 chat/explore 判断；ExecutionMode 提供
        requires_confirmation() / is_interactive() 供审批链路使用。
层&依赖：domain 层（值对象），依赖 shared
"""

from flypig.shared.base import ValueObject

# ── 模式取值 ──
MODE_CHAT = "chat"
MODE_EXPLORE = "explore"
MODE_EXECUTE = "execute"


class ModeConfig(ValueObject):
    """执行模式配置值对象"""

    def __init__(self, name: str = MODE_EXPLORE) -> None:
        self._name = name

    def is_explore(self) -> bool:
        return self._name == MODE_EXPLORE

    def is_chat(self) -> bool:
        return self._name == MODE_CHAT

    def __str__(self) -> str:
        return self._name


class ExecutionMode(ValueObject):
    """执行模式值对象 — 定义 AI 的对话/探索模式"""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def requires_confirmation(self) -> bool:
        """execute 模式会改文件/跑命令，必须经用户确认"""
        return self._value == MODE_EXECUTE

    def is_interactive(self) -> bool:
        """chat / explore 属于交互模式，可直接回复"""
        return self._value in (MODE_CHAT, MODE_EXPLORE)

    def __str__(self) -> str:
        return self._value
