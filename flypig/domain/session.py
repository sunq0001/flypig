"""会话聚合根

为什么做：用户与 AI 的对话以"会话"为单位组织，需要记录会话元数据（ID/时间/标题/状态）。
实现方法：Session(AggregateRoot) + SessionId(ValueObject) + SessionStatus(ValueObject)。
实现效果：会话管理有统一的数据结构，历史会话列表和断点恢复使用同一模型。
技术栈：AggregateRoot, ValueObject, DomainEvent

层&依赖：domain 层，零依赖
细节见文档：docs/docs_refactor/backend-modules.md → §SessionService
"""

from flypig.shared.base import AggregateRoot, ValueObject


class SessionId(ValueObject):
    """会话 ID 值对象"""

    pass


class SessionStatus(ValueObject):
    """会话状态值对象（active / archived / closed）"""

    pass


class Session(AggregateRoot):
    """会话聚合根 — 管理消息、轮次、状态"""

    pass
