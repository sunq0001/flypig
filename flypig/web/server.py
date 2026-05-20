"""FlyPig Web Server — Quart + 原生 WebSocket

HTTP API + WebSocket (/ws/chat + /ws/pty/<id>) 都在单端口 8321，
由 Hypercorn (ASGI) 统一处理。
"""

import asyncio
import json
import os
import sys
import threading
import uuid
import webbrowser
from pathlib import Path
from typing import Optional

from quart import (
    Quart, copy_current_websocket_context,
    jsonify, request, send_from_directory, websocket,
)

from ..hooks import WsEventHook


# ═══════════════════════════════════════════════════════════════
# 全局状态
# ═══════════════════════════════════════════════════════════════

_config = None
_agent = None
_hook: Optional[WsEventHook] = None
_workspace = ""

# /ws/chat 的客户端集合（用于广播）
_ws_clients: set = set()
_ws_senders: dict[str, callable] = {}  # id -> async send(data: str)


# ═══════════════════════════════════════════════════════════════
# Quart 应用
# ═══════════════════════════════════════════════════════════════

static_dir = Path(__file__).parent / "static"
app = Quart(__name__, static_folder=str(static_dir), static_url_path="")
from .terminal import TerminalManager
_terminal_manager = TerminalManager()


# ── HTTP 路由 ──

@app.route("/")
async def index():
    return await send_from_directory(str(static_dir), "index.html")


# ── 文件浏览 API ──

@app.route("/api/files")
async def api_list_files():
    """列出目录内容"""
    path = request.args.get("path", ".")
    base = Path(_workspace)
    target = (base / path).resolve() if path != "." else base

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
async def api_read_file():
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
async def api_config():
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
async def api_set_workspace():
    """设置工作区"""
    global _workspace
    data = await request.get_json(force=True)
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
async def api_save_apikey():
    """保存 API Key"""
    global _config
    if _config is None:
        return jsonify({"error": "not initialized"}), 400
    data = await request.get_json(force=True)
    provider = data.get("provider", "")
    key = data.get("api_key", "")
    if not provider or not key:
        return jsonify({"error": "provider and api_key required"}), 400
    _config.save_api_key(provider, key)
    return jsonify({"ok": True})


@app.route("/api/config/select-model", methods=["POST"])
async def api_select_model():
    """选择模型（返回完整配置供后续初始化）"""
    data = await request.get_json(force=True)
    name = data.get("name", "")
    if not name:
        return jsonify({"error": "no model name"}), 400
    model_cfg = _config.find_model(name) if _config else None
    if not model_cfg:
        return jsonify({"error": f"model '{name}' not found"}), 404
    return jsonify(model_cfg)


# ── Agent 初始化 / 执行 API ──

@app.route("/api/init", methods=["POST"])
async def api_init_agent():
    """初始化 Agent（选择工作区、模型后调用）"""
    global _agent, _hook, _config, _workspace
    from ..config import Config
    from ..model import ModelAdapter
    from ..cost import CostTracker
    from ..tools import ToolExecutor
    from ..agent import Agent
    from ..sandbox import create_sandbox_components, PathValidator

    data = await request.get_json(force=True) or {}

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

    _hook = WsEventHook()
    _hook.set_loop(asyncio.get_event_loop())
    _hook.set_broadcaster(ws_broadcast)
    _agent = Agent(
        model=model,
        cost_tracker=cost_tracker,
        tools=tools,
        system_prompt=ws_prompt,
        hooks=[_hook],
    )

    _scan_workspace_tree()

    return jsonify({"ok": True, "workspace": workspace, "model": model_name})


@app.route("/api/agent/command", methods=["POST"])
async def api_agent_command():
    """处理 / 命令（reset/cost 等）"""
    global _agent
    data = await request.get_json(force=True)
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


# ── 工作区文件树 ──

_tree_cache: dict = {}
_tree_cache_lock = threading.Lock()


def _scan_workspace_tree():
    """扫描工作区生成完整目录树缓存（同步，线程安全）"""
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
async def api_file_tree():
    """返回完整目录树（JSON）"""
    with _tree_cache_lock:
        return jsonify(_tree_cache)


# ═══════════════════════════════════════════════════════════════
# WebSocket — AI 对话通道 /ws/chat
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws/chat")
async def ws_chat():
    """AI 对话 WebSocket 通道

    接收:
        {"type":"chat","msg":"..."}
        {"type":"card_action","card_id":"x","action":"retry|stop|open_in_terminal"}

    发送:
        {"type":"thinking","content":"..."}
        {"type":"tool_call","name":"bash","args":{...}}
        {"type":"tool_result","name":"bash","result":"...","status":"..."}
        {"type":"response","content":"..."}
        {"type":"summary","content":"..."}
        {"type":"error","content":"..."}
        {"type":"done"}
    """
    client_id = str(uuid.uuid4())

    # 用 copy_current_websocket_context 包裹 send，保留 WS 上下文供广播使用
    @copy_current_websocket_context
    async def send_msg(data: str):
        await websocket.send(data)

    _ws_senders[client_id] = send_msg
    try:
        # 发送连接确认
        await websocket.send(json.dumps({"type": "connected"}))

        # Quart 不支持 async for 迭代 websocket，必须用 receive()
        while True:
            message = await websocket.receive()
            if message is None:
                break

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"type": "error", "content": "invalid JSON"}))
                continue

            msg_type = data.get("type", "")

            if msg_type == "chat":
                text = data.get("msg", "").strip()
                if not text:
                    continue
                if _agent is None:
                    await websocket.send(json.dumps({"type": "error", "content": "agent not initialized"}))
                    continue

                # 在线程池中运行 Agent（阻塞的同步调用）
                # 使用 _agent_lock 防止并发 Agent 调用
                asyncio.get_event_loop().run_in_executor(None, _run_agent_locked, text)

            elif msg_type == "card_action":
                await _handle_card_action(data)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        import traceback
        print(f"  [CHAT WS] {client_id} error: {e}")
        traceback.print_exc()
    finally:
        _ws_senders.pop(client_id, None)


# ── 卡片操作 ──

_command_cards: dict[str, dict] = {}  # card_id -> {"command": str, "status": str}


async def _handle_card_action(data: dict):
    """处理卡片操作"""
    card_id = data.get("card_id", "")
    action = data.get("action", "")
    card = _command_cards.get(card_id)

    if action == "stop":
        # 中止当前命令
        _stop_current_command()

    elif action == "retry":
        # 重试命令
        if card and card.get("command"):
            cmd = card["command"]
            asyncio.get_event_loop().run_in_executor(None, _run_bash_command, cmd, card_id)

    elif action == "open_in_terminal":
        # 在用户终端中打开
        if card and card.get("command"):
            cmd = card["command"]
            _write_to_terminal(cmd)


def _stop_current_command():
    """中止当前正在运行的命令"""
    global _agent
    if _agent:
        try:
            _agent.stop()
        except Exception:
            pass


def _run_bash_command(command: str, card_id: str):
    """在后台执行 bash 命令"""
    from ..tools import ToolExecutor
    global _agent
    if not _agent:
        return
    try:
        tool = getattr(_agent, 'tools', None)
        if tool and hasattr(tool, 'execute'):
            result = tool.execute("bash", {"command": command})
            if _hook:
                _hook.on_tool_end("bash", result, {"command": command})
    except Exception as e:
        if _hook:
            _hook.on_tool_end("bash", str(e), {"command": command})


def _write_to_terminal(command: str):
    """将命令写入用户终端"""
    terms = _terminal_manager.list()
    if terms:
        term_id = terms[0]["term_id"]
        term = _terminal_manager.get(term_id)
        if term and term.is_alive():
            term.write((command + "\r\n").encode("utf-8"))


_agent_lock = threading.Lock()
_AGENT_TIMEOUT = 120  # 单次 Agent 执行最大秒数


def _run_agent_locked(message: str):
    """带锁的 Agent 执行（防止并发调用），含超时保护"""
    with _agent_lock:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_run_agent_inner, message)
            try:
                fut.result(timeout=_AGENT_TIMEOUT)
            except concurrent.futures.TimeoutError:
                if _hook:
                    _hook._broadcast({"type": "error", "content": f"执行超时（{_AGENT_TIMEOUT}秒）"})
                    _hook._broadcast({"type": "done"})


def _run_agent_inner(message: str):
    """在后台线程中运行 Agent（同步阻塞调用）"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        _agent.run(message)
        summary = _agent.get_session_summary()
        if _hook:
            _hook._broadcast({"type": "summary", "content": summary})
    except Exception as e:
        if _hook:
            _hook._broadcast({"type": "error", "content": str(e)})
    finally:
        if _hook:
            _hook._broadcast({"type": "done"})
        loop.close()


# ═══════════════════════════════════════════════════════════════
# WebSocket — PTY 终端通道 /ws/pty/<term_id>
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws/pty/<term_id>")
async def ws_pty(term_id: str):
    """PTY 终端 WebSocket 通道

    架构：PTY 读用线程池独立运行，WS 收发在 async handler 中处理。
    和旧 Flask 实现同样的双线程模型，只是 WS API 变成 Quart async。
    """
    import asyncio
    import threading

    term = _terminal_manager.get(term_id)
    if not term:
        term = _terminal_manager.create(term_id, cwd=_workspace)
    if not term.is_alive():
        return

    loop = asyncio.get_event_loop()
    stop_event = threading.Event()

    # 用 @copy_current_websocket_context 持住 WS 发送上下文（供后台线程调用）
    @copy_current_websocket_context
    async def pty_send(data: bytes):
        await websocket.send(data)

    def pty_reader():
        """后台线程：循环读 PTY 输出，通过 event loop 推送到 WS"""
        while term.is_alive() and not stop_event.is_set():
            data = term.read(4096)
            if data is None:
                break
            if data:
                try:
                    fut = asyncio.run_coroutine_threadsafe(pty_send(data), loop)
                    fut.result(timeout=10)
                except Exception:
                    break
            else:
                threading.Event().wait(0.01)

    reader_thread = threading.Thread(target=pty_reader, daemon=True,
                                     name=f"pty-read-{term_id}")
    reader_thread.start()

    try:
        while True:
            msg = await websocket.receive()
            if msg is None:
                break
            if isinstance(msg, bytes):
                term.write(msg)
            elif isinstance(msg, str):
                try:
                    cmd = json.loads(msg)
                    if cmd.get("type") == "resize":
                        term.resize(cmd["cols"], cmd["rows"])
                    continue
                except json.JSONDecodeError:
                    pass
                term.write(msg.encode("utf-8"))
    except Exception:
        pass
    finally:
        stop_event.set()
        _terminal_manager.destroy(term_id)


# ═══════════════════════════════════════════════════════════════
# 广播 — 从 WsEventHook 调用
# ═══════════════════════════════════════════════════════════════

async def ws_broadcast(data: dict):
    """广播事件到所有 /ws/chat 客户端（由 WsEventHook 通过 call_soon_threadsafe 触发）"""
    message = json.dumps(data, ensure_ascii=False)
    dead = []
    for cid, send in list(_ws_senders.items()):
        try:
            await send(message)
        except Exception:
            dead.append(cid)
    for cid in dead:
        _ws_senders.pop(cid, None)


# _broadcast_sync 已弃用，改用 WsEventHook 直接调用 asyncio.run_coroutine_threadsafe


# ═══════════════════════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════════════════════

def start_server(config, host: str = "127.0.0.1", port: int = 8321,
                  open_browser: bool = True):
    """启动 Hypercorn ASGI 服务器（单端口：HTTP + WS）"""
    global _config, _workspace, _tree_cache

    _config = config
    _workspace = config.workspace

    _scan_workspace_tree()

    url = f"http://{host}:{port}"
    print(f"\n  [FlyPig Web UI] 启动服务器...")
    print(f"  [Quart + Hypercorn] {url}")
    print(f"  [工作区] {_workspace}")
    print()

    if open_browser:
        webbrowser.open(url)

    # 启动 Hypercorn
    import hypercorn.asyncio
    import hypercorn.config as hcfg

    hconfig = hcfg.Config()
    hconfig.bind = [f"{host}:{port}"]
    hconfig.use_reloader = False

    try:
        asyncio.run(hypercorn.asyncio.serve(app, hconfig))
    except KeyboardInterrupt:
        print("\n  [FlyPig] 服务器已停止")
