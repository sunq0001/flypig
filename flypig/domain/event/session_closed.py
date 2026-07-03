"""领域事件 — 会话已关闭

为什么做：Session 关闭后需要发出事件，触发清理/存档/资源释放。
实现方法：SessionClosed(DomainEvent) 携带 session_id, reason。

层&依赖：domain.event 层，依赖 shared
"""

from flypig.shared.base import DomainEvent


class SessionClosed(DomainEvent):
    """会话已关闭事件"""
    pass
