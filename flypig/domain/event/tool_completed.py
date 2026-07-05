"""领域事件 — 工具执行已完成

为什么做：工具执行完成后需要发出事件，携带执行结果以便后续流程处理。
实现方法：ToolCompleted(DomainEvent) 携带 tool_name, result, duration_ms。

层&依赖：domain.event 层，依赖 shared
"""

from flypig.shared.base import DomainEvent


class ToolCompleted(DomainEvent):
    """工具执行已完成事件"""

    pass
