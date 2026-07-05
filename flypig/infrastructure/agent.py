"""存根实现 — TODO: 替换为真实实现

为什么做：满足 architecture_check 接口契约检查。
实现方法：继承 IAgent 接口，方法体留空。
层&依赖：infrastructure 层，依赖 domain.interfaces.iagent
"""
from __future__ import annotations
from collections.abc import AsyncGenerator
from flypig.domain.interfaces.iagent import IAgent


class Agent(IAgent):
    """Agent 存根实现"""
    async def run(self, user_input: str, session_id: str | None = None, **kwargs) -> AsyncGenerator[dict, None]:
        yield {}
        if False:
            yield  # pragma: no cover

    async def stop(self) -> None:
        pass

    async def status(self) -> dict:
        return {"status": "stub"}
