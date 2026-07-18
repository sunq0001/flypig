"""ToolTask — 后台任务管理工具

为什么做：AI 启动后台命令后需要检查状态/输出。
实现方法：通过 task_id 查询 ToolBash 中的后台进程。

层&依赖：infrastructure.tools.system 层
"""

from __future__ import annotations

from flypig.infrastructure.tools.registry import tool


@tool(name="task_status", category="system", description="Check background task status")
class ToolTaskStatus:
    """查询后台任务状态"""

    def __init__(self) -> None:
        self._results: dict[str, str] = {}

    async def __call__(self, task_id: str | None = None) -> str:
        if not task_id:
            return self._list_all()
        result = self._results.get(task_id)
        if result is None:
            return f"[Error] Task not found: {task_id}"
        return result

    def _list_all(self) -> str:
        if not self._results:
            return "[Background Tasks] No tasks."
        lines = ["[Background Tasks]"] + [f"  {tid}" for tid in self._results]
        return "\n".join(lines)

    def store(self, task_id: str, result: str) -> None:
        """存储后台任务结果（由 ToolBash 调用）"""
        self._results[task_id] = result
