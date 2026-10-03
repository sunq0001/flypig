"""会话聚合根

为什么做：用户与 AI 的对话以"会话"为单位组织，需要记录会话元数据（ID/时间/标题/状态）。
实现方法：Session(AggregateRoot) + SessionId(ValueObject) + SessionStatus(ValueObject)。

层&依赖：domain 层，零依赖
细节见文档：docs/docs_refactor/backend-modules.md → §SessionService
"""

from datetime import datetime

from flypig.domain.message_entity import Message
from flypig.shared.base import AggregateRoot, ValueObject


class SessionId(ValueObject):
    """会话 ID 值对象"""

    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value

    def to_sse_event(self) -> str:
        """转换为 SSE 事件 ID"""
        return self._value


class SessionStatus(ValueObject):
    """会话状态值对象（active / archived / closed）"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"

    def __init__(self, value: str = ACTIVE) -> None:
        self._value = value

    def is_active(self) -> bool:
        """是否为活跃状态"""
        return self._value == self.ACTIVE

    def can_transition_to(self, target: str) -> bool:
        """状态机：仅 active 可转为 archived / closed，后两者为终态"""
        if self._value == self.ACTIVE:
            return target in (self.ARCHIVED, self.CLOSED)
        return False


class Session(AggregateRoot):
    """会话聚合根 — 管理消息、轮次、状态"""

    def __init__(self, session_id: SessionId, title: str = "") -> None:
        self._id = session_id
        self._title = title
        self._status = SessionStatus()
        self._messages: list[Message] = []
        self._created_at = datetime.now()
        self._updated_at = datetime.now()

    @property
    def title(self) -> str:
        """会话标题"""
        return self._title

    @property
    def messages(self) -> list[Message]:
        """会话内的消息列表（只读视图，变更请走 add_message）"""
        return list(self._messages)

    @property
    def status(self) -> SessionStatus:
        """当前会话状态"""
        return self._status

    def add_message(self, message: Message) -> None:
        """追加消息到会话，并刷新更新时间"""
        self._messages.append(message)
        self._updated_at = datetime.now()

    def change_title(self, title: str) -> None:
        """修改会话标题，并刷新更新时间"""
        self._title = title
        self._updated_at = datetime.now()

    def close(self) -> None:
        """关闭会话（终态）"""
        self._status = SessionStatus(SessionStatus.CLOSED)
        self._updated_at = datetime.now()

    def archive(self) -> None:
        """归档会话（终态）"""
        self._status = SessionStatus(SessionStatus.ARCHIVED)
        self._updated_at = datetime.now()
