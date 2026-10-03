"""Agent 运行时状态

为什么做：LangGraph StateGraph 需要统一的 TypedDict 定义运行时状态。
         文档定义见 docs/docs_refactor/langgraph-graph.md → §AgentState。

实现方法：AgentState 作为 TypedDict，包含对话消息/会话信息/审批/审查/建议等完整字段。
         所有字段除 messages/session_id 外皆为 Optional，R1 阶段只用基础字段。

层&依赖：domain 层，零外部依赖
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class AgentState(TypedDict):
    """Agent 运行时状态，供 LangGraph StateGraph 使用"""

    # ── 基础字段（R1 必用）──
    messages: list[dict[str, Any]]
    session_id: str
    mode: str  # explore / plan / execute
    turn_id: int

    # ── 角色 / 模式（R1.5 启用）──
    persona: NotRequired[str]  # developer / reviewer / tester / ...

    # ── 审批 / 审查（R2+ 启用）──
    pending_approval: NotRequired[dict[str, Any] | None]
    change_review: NotRequired[dict[str, Any] | None]
    rejected_changes: NotRequired[list[dict[str, Any]] | None]
    change_score: NotRequired[dict[str, Any] | None]
    adversarial_suggestion: NotRequired[dict[str, Any] | None]

    # ── 测试 / Git（R2+ 启用）──
    test_results: NotRequired[str | None]
    git_snapshot: NotRequired[str | None]

    # ── 任务（R3+ 启用）──
    active_tasks: NotRequired[list[dict[str, Any]] | None]
