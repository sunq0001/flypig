"""消息实体

为什么做：对话中的每条消息需要唯一标识（MessageId + role + content + timestamp）。
实现方法：Message(Entity) + MessageId(ValueObject)。

TODO: 填充业务方法后移除 __init__ 中字段定义

层&依赖：domain 层，依赖 shared
"""

from datetime import datetime
from flypig.shared.base import Entity, ValueObject


class MessageId(ValueObject):
    """消息 ID 值对象"""

    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MessageId):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


class Message(Entity):
    """消息实体 — 每条对话消息有唯一 ID"""

    def __init__(self, msg_id: MessageId, role: str, content: str) -> None:
        self._id = msg_id
        self._role = role
        self._content = content
        self._timestamp = datetime.now()

    @property
    def role(self) -> str:
        return self._role

    @property
    def content(self) -> str:
        return self._content

    def edit_content(self, new_content: str) -> None:
        """TODO: 编辑消息内容"""
        ...

    def is_from_user(self) -> bool:
        """TODO: 判断是否为用户消息"""
        return self._role == "user"

    def to_llm_message(self) -> dict:
        """TODO: 转换为 LLM API 的消息格式"""
        return {"role": self._role, "content": self._content}
