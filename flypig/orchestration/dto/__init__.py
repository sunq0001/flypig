"""__init__

为什么做：DTO 是应用服务与接口层之间的数据契约，隔离 API 格式与领域模型

实现方法：@dataclass 定义纯数据结构，不含业务逻辑。接口层负责序列化

层&依赖：orchestration.dto 层
"""

from flypig.orchestration.dto.chat_response import ChatResponse

__all__ = [
    "ChatResponse",
]
