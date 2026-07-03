"""Handler — 消息发送后的处理

为什么做：消息发送后需要执行用量追踪、持久化存储、WebSocket 广播。
实现方法：MessageSentHandler 通过 DI 注入后注册到 EventBus。

层&依赖：domain.event 层，依赖 flypig.domain.event.message_sent
"""

from flypig.domain.event.message_sent import MessageSent


class MessageSentHandler:
    """消息发送事件处理器"""
    async def handle(self, event: MessageSent) -> None:
        """TODO: 用量追踪、持久化"""
