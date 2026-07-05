"""任务实体

为什么做：AI 拆解的每个子任务需要统一数据结构（状态/反馈/统计）。
实现方法：TaskItem(Entity) 包含 task_id, description, status, feedback。
实现效果：任务看板、回溯快照、Dashboard 统计都用同一模型。

层&依赖：domain 层，零依赖
细节见文档：docs/docs_refactor/mem_convStore_tasks.md → §任务状态
"""

from flypig.shared.base import Entity


class TaskItem(Entity):
    """任务实体 — AI 拆解的每个子任务"""

    pass
