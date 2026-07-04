"""chat_response

为什么做：应用服务不应直接拼 SSE 格式字符串，应返回结构化 DTO，由接口层负责序列化

实现方法：@dataclass 定义 ChatResponse，type/content/metadata 三个字段，to_sse() 方法序列化为 SSE 格式

层&依赖：application.dto 层
"""

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional


@dataclass
class ChatResponse:
    """聊天响应 DTO — 应用服务与接口层之间的契约

    包含流式对话的所有事件类型：
        - text-start / text-delta / text-end: 文本生成
        - tool-call / tool-result: 工具调用
        - finish: 完成
        - error: 错误
    """
    type: str
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        """序列化为 SSE 格式字符串（由接口层调用）"""
        payload: Dict[str, Any] = {"type": self.type}
        if self.content is not None:
            if self.type in ("text-delta", "text-start", "text-end"):
                payload["delta"] = self.content
            else:
                payload["content"] = self.content
        payload.update(self.metadata)
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @classmethod
    def text_delta(cls, content: str) -> "ChatResponse":
        return cls(type="text-delta", content=content)

    @classmethod
    def text_start(cls) -> "ChatResponse":
        return cls(type="text-start", content="")

    @classmethod
    def text_end(cls) -> "ChatResponse":
        return cls(type="text-end", content="")

    @classmethod
    def finish(cls) -> "ChatResponse":
        return cls(type="finish")

    @classmethod
    def error(cls, message: str) -> "ChatResponse":
        return cls(type="error", content=message)
