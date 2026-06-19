"""Quart 应用入口 + 路由注册

为什么做：所有 API 端点需要注册到 Quart 实例，并配置中间件（CORS/日志/SSE）。
实现方法：create_app() 工厂函数，注册 12 个路由蓝图 → 配置 SSE 队列 → CORS → 日志中间件 → Hypercorn 启动。
实现效果：新增蓝图只需在工厂中加一行，路由代码独立专注业务。
技术栈：Quart, blueprint, SSE, CORS, Hypercorn

层&依赖：backend 层，依赖 backend/routes 所有蓝图 + core/app + infrastructure 中间件
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""