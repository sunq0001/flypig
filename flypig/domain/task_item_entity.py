"""任务项实体

为什么做：AI 助手在对话中可能产生待办任务，需要跟踪状态。
实现方法：TaskItem(Entity) 记录任务描述、状态、截止时间。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import Entity


class TaskItem(Entity):
    """任务项实体 — 待办任务"""

    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"

    def __init__(self, description: str) -> None:
        self._description = description
        self._status = self.PENDING

    @property
    def status(self) -> str:
        return self._status

    def complete(self) -> None:
        """TODO: 标记任务完成"""
        ...

    def cancel(self) -> None:
        """TODO: 取消任务"""
        ...

    def is_done(self) -> bool:
        return self._status == self.DONE
