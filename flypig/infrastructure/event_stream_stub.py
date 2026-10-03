"""存根实现 — TODO: 替换为真实实现

为什么做：满足 architecture_check 接口契约检查，防止 pre-commit 拦截。
实现方法：继承 domain/interfaces 的 ABC，方法体留空或返回默认值。
层&依赖：infrastructure 层，依赖对应的 domain.interfaces 接口
"""

from flypig.domain.interfaces.ievent_stream import IEventStream


class EventStream(IEventStream):
    """事件流存根"""

    async def push(self, session_id: str, event: str, data: dict) -> None:
        pass

    async def pop(self, session_id: str, timeout: float = 30.0) -> dict | None:
        return None

    def cleanup(self, session_id: str) -> None:
        pass
