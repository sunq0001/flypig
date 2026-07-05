"""工具执行器接口

为什么做：所有工具（文件操作/bash/git/搜索/MCP）的调用需要统一入口。

实现方法：IToolExecutor ABC 定义 execute() 核心方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class IToolExecutor(ABC):
    """工具执行器接口 — 统一工具调用入口"""

    @abstractmethod
    async def execute(self, tool_call: Any) -> Any: ...
