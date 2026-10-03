"""Node 工厂：工具执行节点

为什么做：LangGraph 的 execute 节点接收 AI 的 tool_calls 并执行。
         执行出错时 safe_node 捕获异常，将错误消息写入 state，
         然后走 execute → chat 边回到 LLM，LLM 看到错误后可重试。

实现方法：execute_node 接收 state 中最后一次 AI 响应的 tool_calls，
         调 IToolExecutor.execute() 执行，结果写回 state。

安全机制：
  - safe_node 装饰器捕获所有异常，防止节点崩溃导致整图中断
  - 错误信息以 assistant role 写回 messages → 回到 chat 节点
  - router 有 MAX_TURNS=25 上限，防止反复调坏工具的死循环

层&依赖：domain.agent 层，依赖 domain.interfaces.itool_executor + domain.agent_state
"""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger as _log

from flypig.domain.agent.nodes import safe_node
from flypig.domain.agent_state import AgentState
from flypig.domain.interfaces.itool_executor import IToolExecutor
from flypig.shared.constants import ERROR_TRUNCATE_LENGTH

# ── AgentState / 消息字典的字段名 ──
KEY_MESSAGES = "messages"
KEY_TOOL_CALLS = "tool_calls"
KEY_TURN_ID = "turn_id"


def execute_node(
    tool_executor: IToolExecutor,
    on_tool_event: Callable[[str, str, dict, str | None], None] | None = None,
) -> Callable:
    """创建工具执行节点（safe_node 包裹）

    Args:
        tool_executor: 工具执行器实例
        on_tool_event: 可选回调，每次工具调用 call/result 时触发
                       (phase, name, args, result_or_None)

    Returns:
        safe_node 包裹的异步节点函数
    """
    return safe_node(
        _build_execute(tool_executor, on_tool_event),
        node_name="execute",
    )


def _build_execute(
    tool_executor: IToolExecutor,
    on_tool_event: Callable[[str, str, dict, str | None], None] | None,
) -> Callable:
    """构建 execute 节点的原始异步函数（异常由 safe_node 兜底）"""

    async def _execute(state: AgentState) -> AgentState:
        messages = list(state.get(KEY_MESSAGES, []))
        last = messages[-1] if messages else {}

        tool_calls = last.get(KEY_TOOL_CALLS, [])
        if not tool_calls:
            return {**state, KEY_MESSAGES: messages, KEY_TURN_ID: state.get(KEY_TURN_ID, 0) + 1}

        for tc in tool_calls:
            name = tc.get("name", "")
            args = tc.get("arguments", {})

            if on_tool_event:
                on_tool_event("call", name, args, None)

            tool_call_id = tc.get("id", "")
            try:
                result = await tool_executor.execute(name, args)
            except Exception as e:
                # 记录后继续抛出，交由 safe_node 兜底（行为与改造前一致）
                _log.exception(
                    "[execute] 工具 {} 执行失败: {}",
                    name,
                    str(e)[:ERROR_TRUNCATE_LENGTH],
                )
                raise

            if on_tool_event:
                on_tool_event("result", name, args, str(result))

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": str(result),
                }
            )
        return {**state, KEY_MESSAGES: messages, KEY_TURN_ID: state.get(KEY_TURN_ID, 0) + 1}

    return _execute
