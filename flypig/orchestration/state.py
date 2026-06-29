"""AgentState TypedDict

为什么做：LangGraph 的每条消息都需要携带会话 ID、轮次 ID、模式、上下文约束等元数据，不能只用裸消息列表。

实现方法：TypedDict 定义 messages/turn_id/session_id/mode/persona 等字段，零依赖纯数据容器。
所有节点函数共享同一个状态定义。

实现效果：状态结构自文档化，IDE 自动补全，类型安全。

技术栈：typing.TypedDict, messages/turn_id/mode/persona

层&依赖：domain.agent 层，零依赖（纯 typing）
细节见文档：docs/docs_refactor/langgraph-graph.md → §AgentState
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict):
    """LangGraph Agent 状态"""
    messages: list[dict]                # 对话消息列表 [{"role": ..., "content": ...}, ...]
    turn_id: int                        # 当前对话轮次
    session_id: str                     # 会话 ID（关联 ConversationStore）
    persona: str                        # developer/reviewer/tester/...
    mode: str                           # explore / plan / execute
    pending_approval: dict | None       # 待审批请求
    change_review: dict | None          # 变更审查数据
    rejected_changes: list | None       # 被用户驳回的变更
    change_score: dict | None           # 变更评分结果
    adversarial_suggestion: dict | None # 对抗建议卡片
    test_results: str | None            # 测试结果
    git_snapshot: str | None            # Git 快照
    active_tasks: list | None           # 当前会话活跃任务列表
