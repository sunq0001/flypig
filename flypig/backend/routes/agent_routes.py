"""Agent 状态/停止路由 (/api/agent/*)

为什么做：用户需要查看 AI Agent 是否正在运行、当前任务、累成本，以及在需要时强制停止。
实现方法：GET /api/agent/status → Agent 运行状态，POST /api/agent/stop → 强制停止。
实现效果：用户在 Agent 失控或不需要时可以立即停止，不卡死。
技术栈：Quart, /api/agent/status + /api/agent/stop

层&依赖：backend.routes 层，依赖 infrastructure/process_manager.py
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""
