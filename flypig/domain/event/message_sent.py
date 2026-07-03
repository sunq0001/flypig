"""领域事件 — 消息已发送

为什么做：消息发送后需要发出事件，触发存储/用量追踪/WebSocket 广播。
实现方法：MessageSent(DomainEvent) 携带 session_id, message_id, role, token_count。

层&依赖：domain.event 层，依赖 shared
"""

from flypig.shared.base import DomainEvent


class MessageSent(DomainEvent):
    """消息已发送事件"""
    pass
