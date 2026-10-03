"""__init__

为什么做：统一导出所有 DomainEvent 和 EventHandler

实现方法：集中 import + __all__，按事件类型组织文件

层&依赖：domain.event 层
"""

from flypig.domain.event.message_received import MessageReceived
from flypig.domain.event.message_sent import MessageSent
from flypig.domain.event.message_sent_handler import MessageSentHandler
from flypig.domain.event.session_closed import SessionClosed
from flypig.domain.event.session_created import SessionCreated
from flypig.domain.event.session_created_handler import SessionCreatedHandler
from flypig.domain.event.tool_called import ToolCalled
from flypig.domain.event.tool_completed import ToolCompleted
from flypig.domain.event.tool_completed_handler import ToolCompletedHandler

__all__ = [
    "MessageReceived",
    "MessageSent",
    "MessageSentHandler",
    "SessionClosed",
    "SessionCreated",
    "SessionCreatedHandler",
    "ToolCalled",
    "ToolCompleted",
    "ToolCompletedHandler",
]
