"""消息/工具调用/选择题数据类

为什么做：AI 对话产生的消息（用户/AI/系统）、工具调用请求和结果、选择题选项等需要结构化数据表示。

实现方法：@dataclass 定义 Message (role/content/id)、ToolCall (id/name/args)、ChoiceCard (options/selection)。
序列化为 SSE 事件时格式统一。

实现效果：消息类型安全，序列化为 SSE 事件时格式统一。

技术栈：@dataclass, Message/ToolCall/ChoiceCard

层&依赖：domain.models 层，零依赖
细节见文档：docs/docs_refactor/api-reference.md → §SSE 事件格式
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Message:
    """对话消息"""
    role: str  # user / assistant / system / tool
    content: str
    id: str = ""
    tool_calls: list[dict] | None = None  # assistant 消息的工具调用
    tool_call_id: str | None = None       # tool 消息的关联 ID
    name: str | None = None               # tool 消息的工具名

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ChoiceCard:
    """选择题卡片"""
    question: str
    options: list[dict]  # [{"label": "...", "desc": "...", "value": "..."}, ...]
    selected: str | None = None
