"""对话轮次实体

为什么做：每个 session 包含多个 turn（用户消息 → AI 回复），需要记录轮次顺序和关联消息。
实现方法：Turn(Entity) 包含 turn_id, session_id, user_message, ai_response, timestamp。

TODO: 填充业务方法后移除 __init__ 中的字段直接赋值

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import Entity
from flypig.domain.message_entity import MessageId


class Turn(Entity):
    """对话轮次实体 — 记录用户↔AI 的完整一轮交互"""

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._user_message: MessageId | None = None
        self._ai_response: MessageId | None = None
        self._timestamp: float = 0.0

    def add_user_message(self, message_id: MessageId) -> None:
        """TODO: 添加用户消息到轮次"""
        ...

    def add_ai_response(self, message_id: MessageId) -> None:
        """TODO: 添加 AI 回复到轮次"""
        ...

    def is_complete(self) -> bool:
        """TODO: 判断轮次是否结束（用户消息 + AI 回复都存在）"""
        return self._user_message is not None and self._ai_response is not None
