"""graph_routes — LangGraph 可视化蓝图

为什么做：提供浏览器可直接访问的 Mermaid 流程图页面，
         无需 AI 手动粘贴，无需额外启动服务。
         与后端共用同一个 8320 端口，不增加新服务。

实现方法：GET /api/graph/ 返回内嵌 Mermaid.js 的 HTML 页面，
         GET /api/graph/mermaid 返回原始 Mermaid 代码。
         两者都通过 build_graph(dummy_model) 获取图拓扑。

层&依赖：interface.rest.routes 层，依赖 application.graph_factory
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, override

from flypig.domain.interfaces.imodel import IModel
from flypig.domain.interfaces.itool_executor import IToolExecutor
from flypig.orchestration.graph_factory import (
    build_graph,  # pyright: ignore[reportUnknownVariableType]
)
from quart import Blueprint

graph_bp = Blueprint("graph", __name__, url_prefix="/api/graph")


# ── 虚拟模型适配器（仅用于可视化，不调用真实 LLM）──
class _DummyModel(IModel):
    @override
    async def stream(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        messages: list[dict[str, Any]],  # pyright: ignore[reportExplicitAny]
        **kwargs: Any,  # pyright: ignore[reportAny,reportExplicitAny]
    ) -> AsyncGenerator[str, None]:
        # 仅为满足抽象方法签名；可视化场景永远不会调用 stream。
        if False:
            yield  # pyright: ignore[reportUnreachable]

    @override
    def get_model_name(self) -> str:
        return "dummy"


class _DummyToolExecutor(IToolExecutor):
    """虚拟工具执行器（仅用于可视化，不执行真实工具）"""

    @override
    async def execute(self, name: str, arguments: dict[str, Any]) -> str:  # pyright: ignore[reportExplicitAny]
        return f"[Dummy] {name}({arguments})"

    @override
    def get_schemas(self) -> list[dict[str, Any]]:  # pyright: ignore[reportExplicitAny]
        return []


_DUMMY: _DummyModel = _DummyModel()
_DUMMY_TE: _DummyToolExecutor = _DummyToolExecutor()

# ── 本地 mermaid 库（不用 CDN，避免 Tracking Prevention 拦截）──
_MERMAID_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "web"
    / "static_vite"
    / "node_modules"
    / "mermaid"
    / "dist"
    / "mermaid.min.js"
)
_MERMAID_SCRIPT: str = ""
if _MERMAID_PATH.exists():
    with contextlib.suppress(Exception):
        _MERMAID_SCRIPT = _MERMAID_PATH.read_text(encoding="utf-8")  # pyright: ignore[reportConstantRedefinition]

_HTML_PAGE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FlyPig LangGraph 流程图</title>
<script>__MERMAID_SCRIPT__</script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    padding: 24px;
  }
  h1 { font-size: 20px; margin-bottom: 8px; color: #e0e0e0; }
  .info {
    font-size: 13px; color: #888; margin-bottom: 24px;
  }
  .mermaid-container {
    background: #fff; border-radius: 8px; padding: 24px; overflow-x: auto;
  }
  .raw {
    margin-top: 24px; background: #252526; border-radius: 6px; padding: 16px;
    font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 13px;
    white-space: pre-wrap; border: 1px solid #333;
  }
  .raw-label {
    font-size: 12px; color: #888; margin-bottom: 6px;
    text-transform: uppercase; letter-spacing: 1px;
  }
  .actions { margin-bottom: 16px; }
  .actions a {
    color: #4fc3f7; text-decoration: none; font-size: 13px; margin-right: 16px;
  }
  .actions a:hover { text-decoration: underline; }
</style>
</head>
<body>
  <h1>FlyPig LangGraph 流程图</h1>
  <div class="info">__FLOW_INFO__ · 修改 flypig/orchestration/graph_factory.py 即可改变流程</div>
  <div class="actions">
    <a href="/api/graph/mermaid" target="_blank">查看原始 Mermaid 代码</a>
  </div>
  <div class="mermaid-container">
    <pre class="mermaid">__MERMAID_CODE__</pre>
  </div>
  <div class="raw-label">Mermaid 原始代码</div>
  <div class="raw">__MERMAID_CODE__</div>
  <script>mermaid.initialize({ theme: 'default', startOnLoad: true });</script>
</body>
</html>
"""


def _label_mermaid(code: str) -> str:
    """给 Mermaid 条件边（-.->）加上路由条件标签

    根据 router.py 的逻辑：
      tool_calls → execute
      no tool_calls → __end__
    """
    # 用正则匹配灵活处理空白字符
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


@graph_bp.route("/mermaid")
async def get_mermaid() -> str:
    """返回原始 Mermaid 代码"""
    graph = build_graph(_DUMMY, tool_executor=_DUMMY_TE)  # pyright: ignore[reportUnknownVariableType]
    raw: str = graph.get_graph().draw_mermaid()
    return _label_mermaid(raw)


@graph_bp.route("/")
async def graph_page() -> str:
    """返回渲染好的 Mermaid 流程图页面"""
    graph = build_graph(_DUMMY, tool_executor=_DUMMY_TE)  # pyright: ignore[reportUnknownVariableType]
    raw: str = graph.get_graph().draw_mermaid()
    code = _label_mermaid(raw)
    flow_label = (
        "R2: ReAct loop (chat ⇄ execute → end)"
        if "execute" in code and "chat -.->" in code
        else "R1: single chat node"
    )
    html = _HTML_PAGE.replace("__MERMAID_CODE__", code).replace("__FLOW_INFO__", flow_label)
    if _MERMAID_SCRIPT:
        html = html.replace("__MERMAID_SCRIPT__", _MERMAID_SCRIPT)
    else:
        # mermaid 库不可用，用普通 pre 展示 Mermaid 源码
        html = html.replace(
            "<script>__MERMAID_SCRIPT__</script>", "<style>.mermaid{display:none}</style>"
        )
    return html
