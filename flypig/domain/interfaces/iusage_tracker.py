"""用量追踪器接口

为什么做：API 调用次数/token 消耗/费用统计需要统一记录和查询接口。

实现方法：IUsageTracker ABC 定义 record() 和 query() 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class IUsageTracker(ABC):
    """用量追踪器接口 — API 调用统计"""

    @abstractmethod
    async def record(self, event: dict[str, Any]) -> None: ...

    @abstractmethod
    async def query(self, filters: dict[str, Any]) -> list[dict[str, Any]]: ...
