"""ChatChunk — LLM 流式响应的一块数据

为什么做：stream_with_tools 需要返回可能包含文本和 tool_calls 的结构化数据，
         普通 stream 只返回纯文本 token，而 tool 场景需要一并收集工具调用信息。

实现方法：dataclass，text 字段用于逐 token 推流，tool_calls 在流末尾出现。

层&依赖：domain.interfaces 层，零外部依赖

关联文档：docs/docs_refactor/langgraph-graph.md → §chat 节点
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatChunk:
    """LLM 流式响应的一块数据

    - text: 文本 token（可能为空，当 chunk 包含 tool_calls 时）
    - tool_calls: 工具调用列表（仅在流末尾出现）
    """

    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
