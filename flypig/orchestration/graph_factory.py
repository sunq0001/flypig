"""StateGraph 编译工厂

实现方法：GraphFactory 导入 orchestration/state 和 orchestration/nodes，组装 StateGraph → compile。

层&amp;依赖：orchestration 层，依赖 domain/interfaces
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
