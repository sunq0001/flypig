"""MCP 管理 REST 接口

为什么做：前端能力管理面板需要 CRUD、启停、搜索 MCP 服务器的后端接口，不能直接暴露 mcp.json 文件操作给前端。
实现方法：封装 MCP 服务器的增删改查、启停控制、健康检查，注入到 /api/mcp 路由。
实现效果：前端能力面板通过 REST 接口管理所有 MCP 服务器，无需直接操作配置文件。
技术栈：Quart REST, tool_mcp_lifecycle, tool_mcp_discovery

层&依赖：infrastructure.tools.mcp 层，依赖 tool_mcp_loader + tool_mcp_lifecycle + tool_mcp_discovery
细节见文档：docs/docs_refactor/mcp.md → §后端 API
"""
