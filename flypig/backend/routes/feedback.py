"""建议反馈路由 (/api/feedback/suggestion)

为什么做：用户需要对 AI 的对抗建议给出反馈（采纳/拒绝），用于改进后续建议质量。
实现方法：POST 端点记录 suggestion_id + adopted（采纳标志）到数据库。
实现效果：用户的反馈数据沉淀，后续可分析建议采纳率。
技术栈：Quart, POST, suggestion_id + adopted

层&依赖：backend.routes 层，依赖 orchestration/conversation_store.py
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""