"""领域事件 — 消息已接收

为什么做：用户消息进入系统后需要发出事件，触发预处理/路由/日志。
实现方法：MessageReceived(DomainEvent) 携带 session_id, raw_input。

层&依赖：domain.event 层，依赖 shared
"""

from flypig.shared.base import DomainEvent


class MessageReceived(DomainEvent):
    """用户消息已接收事件"""

    pass
