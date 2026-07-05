"""领域事件 — 会话已创建

为什么做：Session 被创建后需要发出事件，通知 handler 初始化存储/统计/日志。
实现方法：SessionCreated(DomainEvent) 携带 session_id, user_id, created_at。

层&依赖：domain.event 层，依赖 shared
关联：SessionCreatedHandler
"""

from flypig.shared.base import DomainEvent


class SessionCreated(DomainEvent):
    """会话已创建事件"""

    pass
