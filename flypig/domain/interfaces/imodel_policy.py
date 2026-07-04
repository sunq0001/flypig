"""imodel_policy

为什么做：不同模型和场景需要不同的执行策略（重试/熔断/超时/回退），需要统一策略接口

实现方法：ABC 定义 execute 方法，包装模型调用，基础设施层实现具体策略

层&依赖：domain.interfaces 层
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Callable


class IModelPolicy(ABC):
    """模型执行策略接口 — 包装模型调用，添加重试/熔断/监控"""

    @abstractmethod
    async def execute(
        self,
        call: Callable[[], AsyncGenerator[str, None]],
    ) -> AsyncGenerator[str, None]:
        """执行模型调用，应用策略逻辑

        Args:
            call: 实际的模型调用函数

        Yields:
            逐 token 结果，策略层可能插入重试/降级逻辑
        """
        ...
