"""对话轮次实体

为什么做：每个 session 包含多个 turn（用户消息 → AI 回复），需要记录轮次顺序和关联消息。
实现方法：Turn(Entity) 包含 turn_id, session_id, user_message, ai_response, timestamp。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import Entity


class Turn(Entity):
    """对话轮次实体 — 记录用户↔AI 的完整一轮交互"""

    pass
