"""MCP 统一网关 — 桥接外部 MCP 工具到 @tool 注册表

为什么做：外部 MCP 服务器（Chrome DevTools、Playwright 等）的工具需要
         桥接到 FlyPig 的 @tool 注册表，走同一个 ReAct 循环（execute → chat）。
实现方法：MCPGateway 读取 mcp.json → 启动子进程 → 发现工具 → 注册到注册表。
层&依赖：infrastructure.tools.mcp 层，依赖 subprocess + registry
"""

from flypig.infrastructure.tools.mcp.tool_mcp_loader import (
    MCPGateway,
    MCPServerProcess,
    get_mcp_gateway,
    init_mcp_gateway,
)

__all__ = [
    "MCPGateway",
    "MCPServerProcess",
    "get_mcp_gateway",
    "init_mcp_gateway",
]
