"""MCP 统一网关 — 加载 MCP 服务器，代理工具到 @tool 注册表

为什么做：FlyPig 的 LLM 需要通过 `@tool` 注册表统一调用所有工具。
         外部 MCP 服务器（Chrome DevTools、Playwright 等）需要桥接
         到这个注册表，走同一个 ReAct 循环（execute → chat）。

实现方法：
  1. MCPGateway 读取 model_registry.json → mcp.servers 配置
  2. 为每个 MCP 服务器启动子进程（MCPServerProcess，见 tool_mcp_server.py）
  3. 调用 tools/list 发现所有可用工具
  4. 自动生成 @tool 装饰器包装类，注册到 _TOOL_REGISTRY
  5. LLM 调工具 → ToolExecutor → MCPGateway → tools/call → 返回结果

工作方式：
  - 启动时自动连接已配置的 MCP 服务器
  - 支持动态启用/禁用（tool_mcp_lifecycle）
  - 超时 + 断线重连

层&依赖：infrastructure.tools.mcp 层，依赖 tool_mcp_server + registry
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger as _log

from flypig.infrastructure.tools.mcp.tool_mcp_server import (
    MCP_SERVERS,
    MCP_TOOL_PREFIX,
    MCPServerProcess,
)
from flypig.infrastructure.tools.registry import tool

# 动态注册的 MCP 工具默认超时（秒）
_MCP_TOOL_TIMEOUT = 120

# ── 转发给 MCP 服务器的 JSON-RPC 字段名 ──
_KEY_NAME = "name"


class MCPGateway:
    """MCP 统一网关 — 管理多个 MCP 服务器，注册工具到 @tool 注册表"""

    def __init__(self, servers: dict | None = None) -> None:
        self._servers: dict[str, MCPServerProcess] = {}
        self._loaded = False
        self._servers_config = servers if servers is not None else MCP_SERVERS
        self._stderr_tasks: list[asyncio.Task] = []

    async def load_all(self) -> list[dict]:
        """加载所有 MCP 服务器，发现工具，注册到 @tool 注册表

        服务器列表来自 model_registry.json → mcp.servers
        不读任何 IDE 配置文件（.codebuddy/ 等）

        Returns:
            所有发现的工具 schema 列表
        """
        if self._loaded:
            return self._get_all_tool_schemas()

        if not self._servers_config:
            return []

        for name, cfg in self._servers_config.items():
            try:
                await self._load_server(name, cfg)
            except Exception as e:
                _log.warning("[mcp] {}: 加载失败 - {}", name, e)

        self._loaded = True
        return self._get_all_tool_schemas()

    async def _load_server(self, name: str, cfg: dict) -> None:
        """加载单个 MCP 服务器"""
        command = cfg.get("command", "")
        args = cfg.get("args", [])
        cwd = cfg.get("cwd")

        server = MCPServerProcess(name, command, args, cwd)
        try:
            await server.start()
        except Exception as e:
            _log.warning("[mcp:{}] 启动失败，跳过该服务器: {}", name, e)
            return

        self._servers[name] = server

        # 读取 stderr（MCP 服务器可能在这输出日志）
        if server._process and server._process.stderr:
            task = asyncio.create_task(self._pipe_stderr(name, server))
            self._stderr_tasks.append(task)

        # 发现工具 → 注册到 @tool 注册表
        tools = await server.discover_tools()
        for tool_def in tools:
            self._register_mcp_tool(name, tool_def, server)

        _log.info("[mcp] {}: {} 个工具已注册", name, len(tools))

    def _register_mcp_tool(
        self, server_name: str, tool_def: dict, server: MCPServerProcess
    ) -> None:
        """将 MCP 工具动态注册到 @tool 注册表"""
        tool_name = tool_def.get(_KEY_NAME, "")
        description = tool_def.get("description", "")

        # 防止名字冲突：加前缀 {prefix}_{server_name}_
        prefixed_name = f"{MCP_TOOL_PREFIX}_{server_name}_{tool_name}"

        # 构建参数 schema
        input_schema = tool_def.get("inputSchema", {})
        properties = input_schema.get("properties", {})

        # 使用 @tool 装饰器动态注册
        @tool(
            name=prefixed_name,
            category=f"mcp/{server_name}",
            timeout=_MCP_TOOL_TIMEOUT,
            description=f"[MCP {server_name}] {description}",
        )
        class DynamicMCPTool:
            """动态生成的 MCP 工具包装类"""

            async def __call__(self, **kwargs: Any) -> str:
                """转发到 MCP 服务器"""
                try:
                    # 只传 inputSchema 里定义的参数
                    filtered = {k: v for k, v in kwargs.items() if k in properties}
                    return await server.call_tool(tool_name, filtered)
                except Exception as e:
                    _log.warning("[mcp] 工具 {} 调用失败: {}", tool_name, e)
                    return f"[Error] MCP 工具 {tool_name} 调用失败: {e}"

    async def _pipe_stderr(self, name: str, server: MCPServerProcess) -> None:
        """管道读取 MCP 服务器的 stderr（调试用）"""
        if not server._process or not server._process.stderr:
            return
        try:
            async for line in server._process.stderr:
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    _log.debug("[mcp:{}] {}", name, text)
        except Exception as e:
            _log.debug("[mcp:{}] stderr 管道结束: {}", name, e)

    def _get_all_tool_schemas(self) -> list[dict]:
        """获取所有已发现工具的 schema"""
        schemas = []
        for server in self._servers.values():
            schemas.extend(server._tools)
        return schemas

    async def shutdown_all(self) -> None:
        """停止所有 MCP 服务器"""
        for name, server in self._servers.items():
            try:
                await server.stop()
            except Exception as e:
                _log.warning("[mcp] {}: 停止失败 - {}", name, e)
        self._servers.clear()

    def get_servers(self) -> dict[str, MCPServerProcess]:
        """获取所有已加载的 MCP 服务器"""
        return dict(self._servers)


# ── 全局单例 — 供 ToolExecutor 调用 ──
_gateway: MCPGateway | None = None


async def init_mcp_gateway() -> MCPGateway:
    """初始化全局 MCP 网关（服务器列表来自 model_registry.json → mcp.servers）"""
    global _gateway
    if _gateway is None:
        _gateway = MCPGateway()
        await _gateway.load_all()
    return _gateway


def get_mcp_gateway() -> MCPGateway | None:
    """获取全局 MCP 网关实例"""
    return _gateway


__all__ = [
    "MCPGateway",
    "MCPServerProcess",
    "get_mcp_gateway",
    "init_mcp_gateway",
]
