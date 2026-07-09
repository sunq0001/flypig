"""MCP 服务器生命周期管理

为什么做：能力管理面板需要启停、禁用/启用 MCP 服务器的能力，而不只是安装和卸载。
实现方法：管理 MCP 服务器子进程的 start/stop/restart/health_check，状态存于内存+持久化到 mcp.json。
实现效果：用户可以在能力面板一键启用/禁用 MCP 服务器，不使用的服务器不占用资源。
技术栈：subprocess, asyncio, 进程管理

层&依赖：infrastructure.tools.mcp 层，依赖 subprocess（管理 MCP 进程）
细节见文档：docs/docs_refactor/mcp.md → §文件结构
"""

# TODO: 骨架文件占位，待具体实现
