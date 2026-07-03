"""Handler — 会话创建后的处理

为什么做：Session 创建后需要执行资源初始化、存储记录、日志等操作。
实现方法：SessionCreatedHandler 实现 EventHandler[SessionCreated]，通过 DI 注入 EventBus。

层&依赖：domain.event 层，依赖 flypig.domain.event.session_created
"""

from flypig.domain.event.session_created import SessionCreated


class SessionCreatedHandler:
    """会话创建事件处理器"""
    async def handle(self, event: SessionCreated) -> None:
        """TODO: 初始化会话存储、记录日志"""
