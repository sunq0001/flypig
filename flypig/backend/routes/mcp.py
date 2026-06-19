"""MCP 路由 /api/mcp/*

为什么做：前端能力管理面板需要 REST 接口操作 MCP 服务器的增删改查、启停、商店搜索。
实现方法：薄路由层，委托到 infrastructure/tools/mcp/ 下的 controller + lifecycle + discovery。
实现效果：前端通过 /api/mcp/* 完成所有能力管理操作。
技术栈：Quart, blueprint

层&依赖：backend 层，依赖 infrastructure.tools/mcp 模块
细节见文档：docs/docs_refactor/mcp.md → §后端 API
"""
