"""Handler — 工具执行完成后的处理

为什么做：工具执行完成后需要记录结果、更新对话上下文、触发后续流程。
实现方法：ToolCompletedHandler 通过 DI 注入后注册到 EventBus。

层&依赖：domain.event 层，依赖 flypig.domain.event.tool_completed
"""

from flypig.domain.event.tool_completed import ToolCompleted


class ToolCompletedHandler:
    """工具执行完成事件处理器"""
    async def handle(self, event: ToolCompleted) -> None:
        """TODO: 记录工具执行结果、更新上下文"""
