"""LangGraph 图谱工厂 — 纯 Python 构建 StateGraph

为什么做：使用纯 Python 定义 LangGraph 流程（替代 YAML 配置方案），
         IDE 原生支持类型检查、代码补全、跳转定义。
         需要可视化时通过 build_graph().get_graph().draw_mermaid() 输出 Mermaid。

实现方法：GraphFactory 委托 build_graph() 构建 StateGraph，
         节点函数从 flypig.domain.agent.nodes 导入，
         条件路由从 flypig.domain.agent.router 导入。

层&依赖：orchestration 层，依赖 domain.agent 节点 + langgraph

可视化：启动 dev.py 后访问 http://localhost:8320/api/graph/ 查看 Mermaid 流程图
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from loguru import logger as _log
from opentelemetry import trace as otel_trace

from flypig.domain.agent.exec_node import execute_node as create_exec_node
from flypig.domain.agent.nodes import chat_node as create_chat_node
from flypig.domain.agent.router import router
from flypig.domain.agent_state import AgentState
from flypig.domain.interfaces.imodel import IModel
from flypig.domain.interfaces.itool_executor import IToolExecutor


def build_graph(  # pyright: ignore[reportUnknownVariableType]
    model: IModel,
    tool_executor: IToolExecutor | None = None,
    on_token: Callable[[str], None] | None = None,
) -> CompiledStateGraph:
    """构建并编译 LangGraph StateGraph

    Args:
        model: 模型适配器实例
        tool_executor: 可选工具执行器（传入后启用 R2 条件路由）
        on_token: 可选 token 回调（用于 SSE 推流）

    Returns:
        编译后的可执行图
    """
    builder = StateGraph(AgentState)

    # ── 注册节点 ──
    builder.add_node("chat", create_chat_node(model, on_token=on_token))

    # ── 流程编排 ──
    builder.add_edge(START, "chat")

    if tool_executor:
        # R2: ReAct 循环（chat ⇄ execute → __end__）
        builder.add_node("execute", create_exec_node(tool_executor))
        builder.add_conditional_edges(
            "chat",
            router,
            {
                "execute": "execute",
                "__end__": "__end__",
            },
        )
        builder.add_edge("execute", "chat")
        _log.info("Graph 已编译: R2 ReAct 模式 (chat ⇄ execute)")
    else:
        # R1: 直接结束
        builder.add_edge("chat", END)
        _log.info("Graph 已编译: R1 基础模式 (chat → END)")

    return builder.compile()


class GraphFactory:
    """LangGraph 图谱工厂 — 按 session 编译/缓存 StateGraph"""

    def __init__(
        self,
        model: IModel,
        tool_executor: IToolExecutor | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> None:
        self._model = model
        self._tool_executor = tool_executor
        self._on_token = on_token
        self._graphs: dict[str, Any] = {}

    def _build_graph(self) -> Any:
        """构建新的 StateGraph 实例"""
        return build_graph(self._model, tool_executor=self._tool_executor, on_token=self._on_token)

    def get_graph(self, session_id: str) -> Any:
        """获取（或创建）会话的编译图"""
        if session_id not in self._graphs:
            self._graphs[session_id] = self._build_graph()
        return self._graphs[session_id]

    def clear_graph(self, session_id: str) -> None:
        """清理会话图缓存"""
        self._graphs.pop(session_id, None)

    async def invoke(self, session_id: str, state: dict[str, Any]) -> AgentState:
        """执行会话图并返回更新后的状态"""
        graph = self.get_graph(session_id)
        _tracer = otel_trace.get_tracer(__name__)

        _log.debug("[graph] 开始执行 (session={}, messages={})", session_id, len(state.get("messages", [])))
        t0 = time.monotonic()

        with _tracer.start_as_current_span("graph.invoke") as span:
            span.set_attribute("session_id", session_id)
            span.set_attribute("message_count", len(state.get("messages", [])))
            result = await graph.ainvoke(state)

        elapsed = time.monotonic() - t0
        turns = result.get("turn_id", 0)
        _log.debug("[graph] 执行完成 (耗时={:.2f}s, turns={})", elapsed, turns)

        return result
