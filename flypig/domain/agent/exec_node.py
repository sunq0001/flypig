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

from flypig.domain.agent_state import AgentState
from flypig.domain.interfaces.itool_executor import IToolExecutor


def execute_node(tool_executor: IToolExecutor):
    """创建工具执行节点

    Args:
        tool_executor: 工具执行器实例

    Returns:
        safe_node 包裹的异步节点函数
    """

    async def _execute(state: AgentState) -> AgentState:
        messages = list(state.get("messages", []))
        last = messages[-1] if messages else {}

        tool_calls = last.get("tool_calls", [])
        if not tool_calls:
            return {**state, "messages": messages, "turn_id": state.get("turn_id", 0) + 1}

        results = []
        for tc in tool_calls:
            name = tc.get("name", "")
            args = tc.get("arguments", {})
            result = await tool_executor.execute(name, args)
            results.append({"name": name, "result": result})

        messages.append({"role": "tool", "content": str(results)})
        return {**state, "messages": messages, "turn_id": state.get("turn_id", 0) + 1}

    from flypig.domain.agent.nodes import safe_node

    return safe_node(_execute, node_name="execute")
