"""__init__

为什么做：应用层负责编排领域逻辑，不包含业务规则

实现方法：ApplicationService 基类 + 具体编排服务。调用 DomainService 和 Repository

层&依赖：application 层
"""

from flypig.application.chat_service import ChatApplicationService

__all__ = [
    "ChatApplicationService",
]
