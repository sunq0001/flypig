"""@tool 装饰器 + 工具注册表

为什么做：工具类用 @tool 装饰器即可自动注册到 _TOOL_REGISTRY，
         无需手动维护注册列表，新增工具只需新建文件 + 加装饰器。
实现方法：_TOOL_REGISTRY 全局字典，@tool() 返回装饰器将类注册进去。

层&依赖：infrastructure.tools 层，纯Python，零依赖
"""

from __future__ import annotations

from typing import Any

_TOOL_REGISTRY: dict[str, type] = {}


def tool(
    name: str | None = None,
    category: str = "system",
    timeout: int = 30,
    description: str = "",
) -> Any:
    """装饰器：将工具类注册到全局注册表

    Args:
        name: 工具名（默认取类名去掉 "Tool" 前缀后小写）
        category: 分组（file/system/search/mcp）
        timeout: 默认超时秒数
        description: 工具描述（用于生成 OpenAI tool schema）

    Usage:
        @tool(name="read_file", category="file")
        class ToolRead:
            async def __call__(self, path: str) -> str: ...
    """

    def decorator(cls: type) -> type:
        tool_name = name or cls.__name__.removeprefix("Tool").lower()
        _TOOL_REGISTRY[tool_name] = cls
        cls._meta = {
            "name": tool_name,
            "category": category,
            "timeout": timeout,
            "description": description or cls.__doc__ or "",
        }
        return cls

    return decorator


def get_registry() -> dict[str, type]:
    """获取工具注册表（只读副本）"""
    return dict(_TOOL_REGISTRY)


def clear_registry() -> None:
    """清空注册表（仅用于测试）"""
    _TOOL_REGISTRY.clear()
