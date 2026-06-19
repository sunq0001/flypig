"""用量查询路由 (/api/usage/*)

为什么做：用户需要查看轮级和会话级的 token/cost/cache 用量统计。
实现方法：GET /api/usage/turn/<id> + /session/<id> + /range + /cache-stats，通过 UsageTrackerService 查询。
实现效果：用户在前端 Dashboard 能看到用量和花费统计。
技术栈：Quart, turn/session/range/cache-stats

层&依赖：backend.routes 层，依赖 orchestration/usage_tracker_service.py
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点、mem_convStore_usage.md → §查询
"""