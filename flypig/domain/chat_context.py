"""对话上下文值对象

为什么做：每次对话需要传递上下文信息（session_id, mode, persona, 当前文件等）。
实现方法：ChatContext(ValueObject) @dataclass(frozen=True)。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class ChatContext(ValueObject):
    """对话上下文值对象 — 不可变，一次对话的快照"""

    pass
