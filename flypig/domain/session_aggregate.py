"""会话聚合根

为什么做：用户与 AI 的对话以"会话"为单位组织，需要记录会话元数据（ID/时间/标题/状态）。
实现方法：Session(AggregateRoot) + SessionId(ValueObject) + SessionStatus(ValueObject)。

TODO: 填充业务方法后移除 __init__ 中的字段直接赋值

层&依赖：domain 层，零依赖
细节见文档：docs/docs_refactor/backend-modules.md → §SessionService
"""

from datetime import datetime
from flypig.shared.base import AggregateRoot, ValueObject
from flypig.domain.message_entity import Message, MessageId


class SessionId(ValueObject):
    """会话 ID 值对象"""

    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value

    def to_sse_event(self) -> str:
        """TODO: 转换为 SSE 事件 ID"""
        return self._value


class SessionStatus(ValueObject):
    """会话状态值对象（active / archived / closed）"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"

    def __init__(self, value: str = ACTIVE) -> None:
        self._value = value

    def is_active(self) -> bool:
        """TODO: 判断是否为活跃状态"""
        return self._value == self.ACTIVE

    def can_transition_to(self, target: str) -> bool:
        """TODO: 判断是否可以转换到目标状态"""
        return True


class Session(AggregateRoot):
    """会话聚合根 — 管理消息、轮次、状态"""

    def __init__(self, session_id: SessionId, title: str = "") -> None:
        self._id = session_id
        self._title = title
        self._status = SessionStatus()
        self._messages: list[Message] = []
        self._created_at = datetime.now()
        self._updated_at = datetime.now()

    def add_message(self, message: Message) -> None:
        """TODO: 添加消息到会话"""
        ...

    def change_title(self, title: str) -> None:
        """TODO: 修改会话标题"""
        ...

    def close(self) -> None:
        """TODO: 关闭会话"""
        ...

    def archive(self) -> None:
        """TODO: 归档会话"""
        ...
