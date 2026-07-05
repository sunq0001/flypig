"""领域事件 — 工具已被调用

为什么做：Agent 发出工具调用请求后需要发出事件，触发执行跟踪/审计/日志。
实现方法：ToolCalled(DomainEvent) 携带 tool_name, arguments, call_id。

层&依赖：domain.event 层，依赖 shared
"""

from flypig.shared.base import DomainEvent


class ToolCalled(DomainEvent):
    """工具已调用事件"""

    pass
