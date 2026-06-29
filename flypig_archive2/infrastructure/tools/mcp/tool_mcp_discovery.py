"""MCP Registry 搜索工具

为什么做：用户需要在能力商店搜索可用的 MCP 服务器，AI 也需要按需发现新能力。
实现方法：封装对官方 MCP Registry 的搜索 API，支持按关键词/分类筛选，返回 Server 元信息。
实现效果：前端能力商店和 AI 自动安装功能可以搜索并安装任意 MCP 服务器。
技术栈：httpx, 官方 MCP Registry API

层&依赖：infrastructure.tools.mcp 层，依赖 httpx（发送 HTTP 请求到 Registry）
细节见文档：docs/docs_refactor/mcp.md → §第二层+第三层
"""
