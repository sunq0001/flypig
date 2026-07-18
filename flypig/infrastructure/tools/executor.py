"""ToolExecutor — 工具执行器（IToolExecutor 实现）

为什么做：从 @tool 注册表加载所有工具，提供统一的 execute() 入口，
         同时生成 OpenAI-compatible tool schema。

实现方法：load() 从 _TOOL_REGISTRY 实例化所有已注册工具，
         execute() 按 name 分发，get_schemas() 输出 OpenAI function calling 格式。

层&依赖：infrastructure.tools 层，实现 domain.interfaces.itool_executor
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from flypig.domain.interfaces.itool_executor import IToolExecutor
from flypig.infrastructure.tools.registry import get_registry


class ToolExecutor(IToolExecutor):
    """工具执行器 — 加载注册表 + 统一调度 + schema 生成"""

    def __init__(self, workspace_dir: Path) -> None:
        self._instances: dict[str, Any] = {}
        self._loaded = False
        self._workspace_dir = workspace_dir
        self.load_all()

    def load_all(self) -> None:
        """从注册表实例化所有工具（含 MCP 网关发现的工具）"""
        import flypig.infrastructure.tools.file as _file_import  # noqa: F401
        import flypig.infrastructure.tools.review as _review_import  # noqa: F401
        import flypig.infrastructure.tools.search as _search_import  # noqa: F401
        import flypig.infrastructure.tools.system as _system_import  # noqa: F401

        registry = get_registry()
        for name, cls in registry.items():
            if name not in self._instances:
                sig = inspect.signature(cls)
                kwargs = {}
                if "workspace_dir" in sig.parameters:
                    kwargs["workspace_dir"] = self._workspace_dir
                self._instances[name] = cls(**kwargs)

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """执行工具"""
        tool = self._instances.get(name)
        if tool is None:
            return f"[Error] Unknown tool: {name}"
        try:
            result = await tool(**arguments)
            return str(result)
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    def get_schemas(self) -> list[dict]:
        """生成 OpenAI function calling schema"""
        schemas = []
        for name, tool in self._instances.items():
            meta = getattr(tool, "_meta", {})
            sig = inspect.signature(tool.__call__ if callable(tool) else type(tool).__call__)

            properties = {}
            required = []
            for pname, param in sig.parameters.items():
                if pname == "self" or pname == "args" or pname == "kwargs":  # noqa: PLR1714
                    continue
                properties[pname] = self._param_to_schema(pname, param)
                if param.default is inspect.Parameter.empty:
                    required.append(pname)

            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": meta.get("description", ""),
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    },
                }
            )
        return schemas

    @staticmethod
    def _param_to_schema(name: str, param: inspect.Parameter) -> dict:  # noqa: ARG004
        """参数 → JSON Schema 类型映射"""
        hint = param.annotation if param.annotation is not inspect.Parameter.empty else str
        type_map = {
            str: {"type": "string"},
            int: {"type": "integer"},
            float: {"type": "number"},
            bool: {"type": "boolean"},
        }
        if hint in type_map:
            return type_map[hint]

        # bool 是 int 的子类，需在 int 之前判断
        origin = getattr(hint, "__origin__", None)
        if origin is not None:
            return {"type": "string"}  # Union/Optional → string fallback

        return {"type": "string"}
