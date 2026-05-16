"""FlyPig Web Server — Flask + SSE 事件推流"""

import json
import os
import queue
import sys
import threading
import uuid
import webbrowser
from pathlib import Path
from typing import Optional

from flask import Flask, Response, jsonify, request, send_from_directory

# ── Agent 模块导入（延迟加载避免循环依赖） ──
from ..hooks import EventHook


# ═══════════════════════════════════════════════════════════════
# 全局状态
# ═══════════════════════════════════════════════════════════════

_config = None
_agent = None
_hook: Optional["WebEventHook"] = None
_event_queues: dict[str, queue.Queue] = {}
_queue_lock = threading.Lock()
_agent_lock = threading.Lock()  # 防止并发 agent 调用
_workspace = ""


# ═══════════════════════════════════════════════════════════════
# Web 事件钩子
# ═══════════════════════════════════════════════════════════════

class WebEventHook(EventHook):
    """Web-specific event hook: 把 Agent 事件广播到所有 SSE 连接"""

    def __init__(self):
        self.session_tokens = 0
        self.session_cost = 0.0
        self.session_tools = 0
        self.bash_history: list = []

    def on_llm_end(self, usage: dict, cost_info: dict, iteration: int):
        total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        cost = cost_info.get("cost", 0)
        self.session_tokens += total
        self.session_cost += cost
        self._broadcast({
            "type": "llm_end",
            "tokens": total,
            "cost": cost,
            "session_tokens": self.session_tokens,
            "session_cost": self.session_cost,
        })

    def on_thinking(self, content: str):
        self._broadcast({"type": "thinking", "content": content})

    def on_tool_start(self, tool_name: str, arguments: dict):
        self._broadcast({
            "type": "tool_start",
            "name": tool_name,
            "arguments": arguments,
        })

    def on_tool_end(self, tool_name: str, result: str, arguments: dict = None):
        truncated = result[:3000] if result else ""
        self._broadcast({
            "type": "tool_end",
            "name": tool_name,
            "result": truncated,
            "arguments": arguments or {},
        })
        # 记录 bash 历史
        if tool_name == "bash" and arguments:
            cmd = arguments.get("command", "")
            if cmd:
                self.bash_history.append(cmd)

    def on_tool_chain_end(self, tool_results: list, cost_info: dict, iteration: int):
        self._broadcast({
            "type": "tool_chain_end",
            "tool_count": len(tool_results),
            "tokens": cost_info.get("input_tokens", 0) + cost_info.get("output_tokens", 0),
            "cost": cost_info.get("cost", 0),
        })

    def on_response(self, content: str, usage_line: str):
        self._broadcast({"type": "response", "content": content})

    def _broadcast(self, data: dict):
        dead = []
        with _queue_lock:
            for qid, q in _event_queues.items():
                try:
                    q.put_nowait(data)
                except queue.Full:
                    dead.append(qid)
            for qid in dead:
                del _event_queues[qid]


# ═══════════════════════════════════════════════════════════════
# Flask 应用
# ═══════════════════════════════════════════════════════════════

static_dir = Path(__file__).parent / "static"
app = Flask(__name__, static_folder=str(static_dir), static_url_path="")


@app.route("/")
def index():
    return send_from_directory(str(static_dir), "index.html")


# ── 文件浏览 API ──

@app.route("/api/files")
def api_list_files():
    """列出目录内容"""
    path = request.args.get("path", ".")
    base = Path(_workspace)
    target = (base / path).resolve() if path != "." else base

    # 安全检查：不允许超出工作区
    try:
        target.relative_to(base)
    except ValueError:
        return jsonify({"error": "path outside workspace"}), 403

    if not target.exists() or not target.is_dir():
        return jsonify({"error": "directory not found"}), 404

    _EXCLUDE = {".git", "node_modules", "__pycache__", ".venv", ".codebuddy",
                ".vscode", ".idea", "venv", "env", "dist", "build", ".tox"}
    _CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
                  ".md", ".txt", ".yaml", ".yml", ".json", ".toml",
                  ".css", ".html", ".sh", ".bat", ".ps1", ".vue"}

    items = []
    try:
        entries = sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return jsonify({"error": "permission denied"}), 403

    for entry in entries:
        if entry.name.startswith(".") or entry.name in _EXCLUDE:
            continue
        is_dir = entry.is_dir()
        if not is_dir and entry.suffix not in _CODE_EXTS:
            continue
        rel = str(entry.relative_to(base))
        items.append({
            "name": entry.name,
            "path": rel.replace("\\", "/"),
            "is_dir": is_dir,
        })

    return jsonify({"items": items, "current": path})


@app.route("/api/file")
def api_read_file():
    """读取文件内容"""
    path = request.args.get("path", "")
    if not path:
        return jsonify({"error": "no path provided"}), 400

    base = Path(_workspace)
    target = (base / path).resolve()

    try:
        target.relative_to(base)
    except ValueError:
        return jsonify({"error": "path outside workspace"}), 403

    if not target.exists() or not target.is_file():
        return jsonify({"error": "file not found"}), 404

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return jsonify({
            "path": path,
            "name": target.name,
            "content": content,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Agent 配置 API ──

@app.route("/api/config")
def api_config():
    """返回当前配置摘要"""
    global _config
    if _config is None:
        return jsonify({"status": "not_initialized"})
    models = []
    for m in _config.models:
        has_key = bool(m.get("api_key"))
        models.append({
            "name": m["name"],
            "provider": m.get("provider", ""),
            "has_key": has_key,
        })
    return jsonify({
        "workspace": _workspace,
        "default_model": _config.default_model_name,
        "models": models,
    })


@app.route("/api/config/workspace", methods=["POST"])
def api_set_workspace():
    """设置工作区"""
    global _workspace
    data = request.get_json(force=True)
    path = data.get("path", "")
    if not path:
        return jsonify({"error": "no path"}), 400
    p = Path(path).resolve()
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
    _workspace = str(p)
    if _config:
        _config._workspace_override = _workspace
    return jsonify({"workspace": _workspace})


@app.route("/api/config/apikey", methods=["POST"])
def api_save_apikey():
    """保存 API Key"""
    global _config
    if _config is None:
        return jsonify({"error": "not initialized"}), 400
    data = request.get_json(force=True)
    provider = data.get("provider", "")
    key = data.get("api_key", "")
    if not provider or not key:
        return jsonify({"error": "provider and api_key required"}), 400
    _config.save_api_key(provider, key)
    return jsonify({"ok": True})


@app.route("/api/config/select-model", methods=["POST"])
def api_select_model():
    """选择模型（返回完整配置供后续初始化）"""
    data = request.get_json(force=True)
    name = data.get("name", "")
    if not name:
        return jsonify({"error": "no model name"}), 400
    model_cfg = _config.find_model(name) if _config else None
    if not model_cfg:
        return jsonify({"error": f"model '{name}' not found"}), 404
    return jsonify(model_cfg)


# ── Agent 执行 API ──

@app.route("/api/init", methods=["POST"])
def api_init_agent():
    """初始化 Agent（选择工作区、模型后调用）"""
    global _agent, _hook, _config, _workspace
    from ..config import Config
    from ..model import ModelAdapter
    from ..cost import CostTracker
    from ..tools import ToolExecutor
    from ..agent import Agent
    from ..sandbox import create_sandbox_components, PathValidator

    data = request.get_json(force=True) or {}

    if _config is None:
        _config = Config()

    workspace = data.get("workspace", _workspace or _config.workspace)
    _workspace = workspace
    _config._workspace_override = workspace

    model_name = data.get("model", "deepseek-v4-flash")
    api_key = data.get("api_key", "")

    model_config = _config.find_model(model_name) or {"name": model_name, "provider": "DeepSeek"}
    if api_key:
        model_config["api_key"] = api_key
    elif not model_config.get("api_key"):
        provider = model_config.get("provider", "")
        model_config["api_key"] = _config.api_keys.get(provider, "")

    if not model_config.get("api_key"):
        return jsonify({"error": "API Key not configured"}), 400

    model = ModelAdapter(model_config)
    cost_tracker = CostTracker(_config.pricing_dict)

    sandbox_cfg = _config.build_sandbox_config()
    sandbox_mgr, path_val = create_sandbox_components(sandbox_cfg, workspace)
    if sandbox_cfg.enabled and sandbox_mgr is None:
        if sandbox_cfg.mode == "mixed":
            path_val = PathValidator(workspace_dir=workspace)
        sandbox_mgr = None

    tools = ToolExecutor(
        workspace_dir=workspace,
        path_validator=path_val,
        sandbox_manager=sandbox_mgr,
    )
    tools._web_mode = True

    from ..pricing_fetcher import fetch_pricing
    prices, _ = fetch_pricing(model_config["name"], model_config.get("provider", ""))
    if prices:
        cost_tracker.set_pricing(model_config["name"], prices)
        api_model = model_config.get("model", "deepseek-chat")
        if api_model != model_config["name"]:
            cost_tracker.set_pricing(api_model, prices)

    ws_prompt = _config.system_prompt + (
        f"\n\nCurrent working directory: {workspace}\n"
        f"All file paths in tool results are relative to this directory.\n"
    )

    _hook = WebEventHook()
    _agent = Agent(
        model=model,
        cost_tracker=cost_tracker,
        tools=tools,
        system_prompt=ws_prompt,
        hooks=[_hook],
    )

    # 重新扫描工作区
    _scan_workspace_tree()

    return jsonify({"ok": True, "workspace": workspace, "model": model_name})


@app.route("/api/run", methods=["POST"])
def api_run_agent():
    """运行 Agent（异步，事件通过 SSE 推送）"""
    global _agent
    if _agent is None:
        return jsonify({"error": "agent not initialized"}), 400
    data = request.get_json(force=True)
    message = data.get("message", "")
    if not message:
        return jsonify({"error": "no message"}), 400

    def _run():
        with _agent_lock:
            try:
                _agent.run(message)
                summary = _agent.get_session_summary()
                _broadcast({"type": "summary", "content": summary})
            except Exception as e:
                _broadcast({"type": "error", "content": str(e)})
            finally:
                _broadcast({"type": "done"})

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/agent/command", methods=["POST"])
def api_agent_command():
    """处理 / 命令（reset/cost 等）"""
    global _agent
    data = request.get_json(force=True)
    cmd = data.get("command", "").lower()

    if cmd == "reset":
        if _agent:
            _agent.reset()
            if _hook:
                _hook.session_tokens = 0
                _hook.session_cost = 0.0
                _hook.session_tools = 0
        return jsonify({"ok": True, "response": "对话已重置"})
    elif cmd == "cost":
        if _agent:
            summary = _agent.get_session_summary()
            return jsonify({"ok": True, "response": summary})
        return jsonify({"ok": True, "response": "未初始化"})
    else:
        return jsonify({"error": f"unknown command: {cmd}"}), 400


# ── SSE 事件推流 ──

@app.route("/api/events")
def api_events():
    """SSE 端点 — 浏览器通过 EventSource 连接到这里接收实时事件"""
    qid = str(uuid.uuid4())
    q: queue.Queue = queue.Queue(maxsize=200)
    with _queue_lock:
        _event_queues[qid] = q

    def generate():
        try:
            while True:
                try:
                    data = q.get(timeout=30)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    # 发送心跳保持连接
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except GeneratorExit:
            pass
        finally:
            with _queue_lock:
                _event_queues.pop(qid, None)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── 工作区文件树 ──

_tree_cache: dict = {}
_tree_cache_lock = threading.Lock()


def _scan_workspace_tree():
    """扫描工作区生成完整目录树缓存"""
    global _tree_cache
    base = Path(_workspace)
    if not base.exists():
        _tree_cache = {}
        return

    _EXCLUDE = {".git", "node_modules", "__pycache__", ".venv", ".codebuddy",
                ".vscode", ".idea", "venv", "env", "dist", "build", ".tox"}
    _CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
                  ".md", ".txt", ".yaml", ".yml", ".json", ".toml",
                  ".css", ".html", ".sh", ".bat", ".ps1", ".vue"}

    def _build_tree(path: Path):
        """递归构建树"""
        children = []
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return {"name": path.name, "path": "", "is_dir": False, "children": []}

        for entry in entries:
            if entry.name.startswith(".") or entry.name in _EXCLUDE:
                continue
            rel = str(entry.relative_to(base)).replace("\\", "/")
            if entry.is_dir():
                sub = _build_tree(entry)
                sub["path"] = rel
                children.append(sub)
            elif entry.suffix in _CODE_EXTS:
                children.append({
                    "name": entry.name,
                    "path": rel,
                    "is_dir": False,
                })
        return {"name": path.name, "path": "", "is_dir": True, "children": children}

    with _tree_cache_lock:
        _tree_cache = _build_tree(base)


@app.route("/api/tree")
def api_file_tree():
    """返回完整目录树（JSON）"""
    with _tree_cache_lock:
        return jsonify(_tree_cache)


# ── 辅助 ──

def _broadcast(data: dict):
    """广播事件（从非 SSE 线程调用）"""
    dead = []
    with _queue_lock:
        for qid, q in _event_queues.items():
            try:
                q.put_nowait(data)
            except queue.Full:
                dead.append(qid)
        for qid in dead:
            del _event_queues[qid]


# ═══════════════════════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════════════════════

def start_server(config, host: str = "127.0.0.1", port: int = 8321,
                  open_browser: bool = True):
    """启动 Flask Web 服务器"""
    global _config, _workspace, _tree_cache

    _config = config
    _workspace = config.workspace

    # 初始化扫描工作区
    _scan_workspace_tree()

    url = f"http://{host}:{port}"
    print(f"\n  [FlyPig Web UI] 启动服务器...")
    print(f"  [URL] {url}")
    print(f"  [工作区] {_workspace}")
    print()

    if open_browser:
        webbrowser.open(url)

    # 使用 Flask 内置服务器（开发用）
    # 生产环境应使用 gunicorn/uvicorn + eventlet
    app.run(host=host, port=port, debug=False, use_reloader=False)
