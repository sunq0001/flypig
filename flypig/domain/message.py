"""消息实体

为什么做：对话中的每条消息需要唯一标识（MessageId + sessionId + role + content + timestamp）。
实现方法：Message(Entity) + MessageId(ValueObject)。
实现效果：消息可作为领域事件载体，支持按 ID 引用和追踪。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import Entity, ValueObject


class MessageId(ValueObject):
    """消息 ID 值对象"""
    pass


class Message(Entity):
    """消息实体 — 每条对话消息有唯一 ID"""
    pass
