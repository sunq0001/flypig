"""事件钩子接口

为什么做：工具调用前后、对话轮次变更等事件需要挂载副作用（日志/用量记录/checkpoint），钩子系统提供统一注册/触发机制。

实现方法：IHook ABC 定义 on_event() 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class IHook(ABC):
    """事件钩子接口 — 挂载事件副作用"""

    @abstractmethod
    async def on_event(self, event_name: str, payload: dict[str, Any]) -> None: ...
