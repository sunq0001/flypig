"""领域事件 — 消息已接收

为什么做：用户消息进入系统后需要发出事件，触发预处理/路由/日志。
实现方法：MessageReceived(DomainEvent) 携带 session_id, raw_input。

层&依赖：domain.event 层，依赖 shared
"""

from flypig.shared.base import DomainEvent


class MessageReceived(DomainEvent):
    """用户消息已接收事件"""

    def describe(self) -> str:
        """返回可读事件摘要（日志/审计用）"""
        return f"会话 {self.aggregate_id or '-'} 收到用户消息 @ {self.occurred_at:%H:%M:%S}"
