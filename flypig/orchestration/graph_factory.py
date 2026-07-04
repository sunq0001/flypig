"""graph_factory

为什么做：LangGraph 的 StateGraph 编译需要封装，避免业务代码直接依赖 LangGraph 细节

实现方法：GraphFactory 组装 nodes + edges，调用 StateGraph.compile() 返回可调用的 graph

层&依赖：orchestration 层，依赖 domain/interfaces
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START

from flypig.orchestration.state import AgentState
from flypig.orchestration.nodes.chat_node import chat_node
from flypig.domain.interfaces.imodel import IModel


class GraphFactory:
    """LangGraph 编译工厂"""

    def __init__(self, model: IModel):
        self._model = model
        self._graphs: dict[str, callable] = {}

    def _build_graph(self) -> callable:
        builder = StateGraph(AgentState)
        builder.add_node("chat", chat_node(self._model))
        builder.add_edge(START, "chat")
        return builder.compile()

    def get_graph(self, session_id: str) -> callable:
        if session_id not in self._graphs:
            self._graphs[session_id] = self._build_graph()
        return self._graphs[session_id]

    def clear_graph(self, session_id: str) -> None:
        self._graphs.pop(session_id, None)
