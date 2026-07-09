"""工具基础设施层

为什么做：统一管理所有 AI 可调用的工具（文件操作/bash/git/搜索/MCP），
         通过 @tool 装饰器自动注册，ToolExecutor 统一调度。
实现方法：registry.py 提供 @tool 装饰器 + _TOOL_REGISTRY，
         executor.py 实现 IToolExecutor 接口从注册表加载工具。

层&依赖：infrastructure.tools 层，依赖 domain.interfaces.itool_executor
"""

from flypig.infrastructure.tools.executor import ToolExecutor
from flypig.infrastructure.tools.registry import get_registry, tool

__all__ = [
    "ToolExecutor",
    "get_registry",
    "tool",
]
