"""MCP 自助安装管理工具

为什么做：AI 遇到没装的 MCP 服务器时，需要自动搜索 MCP Registry 并安装，不需要用户手动操作。
实现方法：封装 mcp-auto-install 的 install_mcp_server 工具，安装时弹审批卡片让用户确认。
实现效果：AI 按需发现和安装 MCP 服务器，用户确认后立即可用。
技术栈：调 mcp-auto-install 的 install_mcp_server 工具

层&依赖：infrastructure.tools.mcp 层，依赖 subprocess + mcp-auto-install
细节见文档：docs/docs_refactor/mcp.md → §第二层+第三层
"""