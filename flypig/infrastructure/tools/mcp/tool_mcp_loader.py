"""MCP 服务器加载注册工具

为什么做：启动时需要自动加载 mcp.json 中预配的 MCP 服务器，将 tools 注册到 LangGraph ToolNode。
实现方法：读取 mcp.json → 启动 MCP 服务器进程 → 发现 tools → 注册到 ToolNode。
实现效果：MCP 服务器开箱即用，用户不需要手动配置。
技术栈：mcp-auto-install, 启动时加载 mcp.json → ToolNode

层&依赖：infrastructure.tools.mcp 层，依赖 subprocess（启动 MCP 进程）
细节见文档：docs/docs_refactor/mcp.md → §三层策略
"""