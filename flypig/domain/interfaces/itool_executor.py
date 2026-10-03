"""工具执行器接口

为什么做：所有工具（文件操作/bash/git/搜索/MCP）的调用需要统一入口。

实现方法：IToolExecutor ABC 定义 execute() 核心方法和 get_schemas()。

层&依赖：domain.interfaces 层，零依赖
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IToolExecutor(ABC):
    """工具执行器接口 — 统一工具调用入口"""

    @abstractmethod
    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """执行工具

        Args:
            name: 工具名
            arguments: 参数字典

        Returns:
            工具执行结果（字符串）
        """
        ...

    @abstractmethod
    def get_schemas(self) -> list[dict]:
        """获取工具 schema 列表（OpenAI function calling 格式）"""
        ...
