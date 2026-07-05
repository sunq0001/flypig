"""对话存储接口

为什么做：历史会话和消息需要持久化，不同后端（SQLite/文件/远程）通过统一接口切换。

实现方法：IConversationStore ABC 定义会话和消息的 CRUD 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class IConversationStore(ABC):
    """对话存储接口 — 会话和消息的持久化"""

    @abstractmethod
    async def save_session(self, session: Any) -> None: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Any | None: ...
