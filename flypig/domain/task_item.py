"""任务数据类

为什么做：AI 拆解的每个子任务需要统一数据结构（状态/反馈/统计），不能散落在各处用 dict。
实现方法：@dataclass 定义 TaskItem (id/description/status/feedback) + TaskStats (total/done/failed/canceled)。
实现效果：任务看板、回溯快照、Dashboard 统计都用同一模型，前端后端一致。
技术栈：@dataclass, TaskItem + user_feedback (ok/good/not_work) + TaskStats

层&依赖：domain.models 层，零依赖
细节见文档：docs/docs_refactor/mem_convStore_tasks.md → §任务状态
"""
