"""Agent 状态值对象

为什么做：Agent 的运行时状态（当前模式/会话ID/步骤计数）需要统一数据结构。
实现方法：AgentState(ValueObject) @dataclass(frozen=True)。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class AgentState(ValueObject):
    """Agent 运行时状态值对象"""

    pass
