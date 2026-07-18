"""Agent 桩实现

为什么做：IAgent 接口需要 infrastructure 层的具体实现才能通过架构 CONTRACT 检查。
实现方法：提供最小化的 IAgent 子类 AgentStub，run() 返回一个占位事件，stop/status 为空操作。

TODO：等待正式 Agent 实现替换此桩代码。

层&依赖：infrastructure 层，实现 domain.interfaces.iagent.IAgent
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from flypig.domain.interfaces.iagent import IAgent


class AgentStub(IAgent):
    """IAgent 占位实现 — 满足架构 CONTRACT 检查的桩代码"""

    async def run(
        self, user_input: str, session_id: str | None = None, **kwargs
    ) -> AsyncGenerator[dict, None]:
        yield {"type": "error", "content": "Agent 实现尚未就绪"}
        if False:
            yield {}  # 让 generator 有类型

    async def stop(self) -> None:
        return

    async def status(self) -> dict:
        return {"running": False, "session_id": None, "mode": ""}
