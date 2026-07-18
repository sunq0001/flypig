"""graph_routes — LangGraph 可视化蓝图

为什么做：提供浏览器可直接访问的 Mermaid 流程图页面，
         无需 AI 手动粘贴，无需额外启动服务。
         与后端共用同一个 8320 端口，不增加新服务。

实现方法：GET /api/graph/ 返回内嵌 Mermaid.js 的 HTML 页面，
         GET /api/graph/mermaid 返回原始 Mermaid 代码。
         两者都通过 build_graph(dummy_model) 获取图拓扑。
         HTML 模板从独立文件读取，模板脚本在请求时惰性加载。

层&依赖：interface.rest.routes 层，依赖 application.graph_factory
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, override

from quart import Blueprint, Response

from flypig.domain.interfaces.chat_chunk import ChatChunk
from flypig.domain.interfaces.imodel import IModel
from flypig.domain.interfaces.itool_executor import IToolExecutor
from flypig.orchestration.graph_factory import (
    build_graph,  # pyright: ignore[reportUnknownVariableType]
)

graph_bp = Blueprint("graph", __name__, url_prefix="/api/graph")

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


# ── 虚拟适配器（仅用于可视化，不调用真实 LLM）──


class _DummyModel(IModel):
    """不调用任何 API 的虚拟模型适配器，仅满足 build_graph 签名"""

    @override
    async def stream(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        return
        yield ""  # pyright: ignore[reportUnreachable]

    @override
    async def stream_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncGenerator[ChatChunk, None]:
        return
        yield ChatChunk()  # pyright: ignore[reportUnreachable]

    @override
    def get_model_name(self) -> str:
        return "dummy"


class _DummyToolExecutor(IToolExecutor):
    """虚拟工具执行器（仅用于可视化，不执行真实工具）"""

    @override
    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        return f"[Dummy] {name}({arguments})"

    @override
    def get_schemas(self) -> list[dict[str, Any]]:
        return []


_DUMMY = _DummyModel()
_DUMMY_TE = _DummyToolExecutor()

# ── 缓存 ──

_GRAPH_CACHE: tuple[str, str] | None = None  # (mermaid_code, flow_label)


def _get_graph() -> tuple[str, str]:
    """获取缓存的图拓扑 Mermaid 代码和流程标签"""
    global _GRAPH_CACHE
    if _GRAPH_CACHE is not None:
        return _GRAPH_CACHE
    graph = build_graph(_DUMMY, tool_executor=_DUMMY_TE)  # pyright: ignore[reportUnknownVariableType]
    raw: str = graph.get_graph().draw_mermaid()
    labeled = _label_mermaid(raw)
    flow_label = (
        "R2: ReAct loop (chat ⇄ execute → end)"
        if "execute" in labeled and "chat -.->" in labeled
        else "R1: single chat node"
    )
    _GRAPH_CACHE = (labeled, flow_label)
    return _GRAPH_CACHE


def _label_mermaid(code: str) -> str:
    """给 Mermaid 条件边（-.->）加上路由条件标签"""
    code = re.sub(
        r"chat\s*-\.->\s*execute\s*;",
        "chat -.->|tool_calls| execute;",
        code,
    )
    code = re.sub(
        r"chat\s*-\.->\s*__end__\s*;",
        "chat -.->|no tool_calls / max_turns| __end__;",
        code,
    )
    return code


def _load_html() -> str:
    """读取 HTML 模板文件（惰性加载）"""
    path = _TEMPLATE_DIR / "graph.html"
    if not path.exists():
        return "<html><body><h1>模板文件不存在</h1></body></html>"
    return path.read_text(encoding="utf-8")


def _load_mermaid_script() -> str:
    """惰性加载本地 mermaid.min.js（避免导入时读文件）"""
    mermaid_path = (
        Path(__file__).resolve().parent.parent.parent
        / "web" / "static_vite" / "node_modules"
        / "mermaid" / "dist" / "mermaid.min.js"
    )
    if not mermaid_path.exists():
        return ""
    try:
        return mermaid_path.read_text(encoding="utf-8")
    except Exception:
        return ""


@graph_bp.route("/mermaid")
async def get_mermaid() -> str:
    """返回原始 Mermaid 代码"""
    code, _ = _get_graph()
    return code


@graph_bp.route("/")
async def graph_page() -> Response:
    """返回渲染好的 Mermaid 流程图页面"""
    code, flow_label = _get_graph()
    html = _load_html()
    mermaid_script = _load_mermaid_script()

    html = (
        html
        .replace("__MERMAID_CODE__", code)
        .replace("__FLOW_INFO__", flow_label)
        .replace("__MERMAID_SCRIPT__", mermaid_script)
    )

    return Response(html, mimetype="text/html")
