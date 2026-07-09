"""Router — LangGraph 条件路由

为什么做：AI 每轮回复后，根据 AgentState 决定下一步走向。
         有工具调用 → execute，有待审批 → approval，否则结束或留在 chat。

实现方法：router(state) 读取 state 中的 messages/pending_approval，
         返回下一个节点名。供 graph_loader 注册条件边使用。

技术栈：langgraph, loguru
层&依赖：domain.agent 层，依赖 domain.agent_state
"""

from __future__ import annotations

from loguru import logger as _log

from flypig.domain.agent_state import AgentState

# 最大对话轮次，超过强制结束防止死循环
_MAX_TURNS = 25


def router(state: AgentState) -> str:
    """条件路由：根据 AgentState 决定下一步

    R1: 仅 chat → end（无条件边）
    R2: ReAct 循环 — 有 tool_calls → execute，无 → end
        execute 出错也会通过 safe_node 带回 chat，LLM 可见错误信息
    R2+: pending_approval → approval
    R3+: 超过 MAX_TURNS → 强制结束

    Args:
        state: 当前 AgentState

    Returns:
        下一节点名称
    """
    # 安全阀：超最大轮次强制结束
    turn_id = state.get("turn_id", 0)
    if turn_id >= _MAX_TURNS:
        _log.warning("[router] 达到最大轮次 {} -> END", turn_id)
        return "__end__"

    messages = state.get("messages", [])
    if not messages:
        _log.debug("[router] 无消息 -> END")
        return "__end__"

    last_msg = messages[-1]

    # R2: AI 请求调工具
    tool_calls = last_msg.get("tool_calls")
    if tool_calls:
        names = [tc.get("name", "?") for tc in tool_calls]
        _log.debug("[router] 检测到 tool_calls: {} -> execute", names)
        return "execute"

    # R2+: 有待审批请求
    if state.get("pending_approval"):
        _log.debug("[router] 有待审批 -> approval")
        return "approval"

    # R1: 默认结束
    _log.debug("[router] 无 tool_calls -> END")
    return "__end__"
