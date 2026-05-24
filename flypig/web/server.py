"""FlyPig Web Server — Quart + SSE (agent 事件) + WS (仅 PTY)

agent 事件通过 SSE 的 threading.Queue 传递，避免 Windows 跨线程广播问题。
WS 仅用于 PTY 终端，不受影响。
实时文件监控：watchfiles 检测工作区变化时自动刷新文件树缓存。
"""
import asyncio
import json
import os
import sys
import threading
import time
import uuid
import webbrowser
import queue as queue_mod
from pathlib import Path
from typing import Optional

from quart import (
    Quart, copy_current_websocket_context,
    jsonify, request, send_from_directory, websocket, Response,
)

from ..hooks import WsEventHook


# ═══════════════════════════════════════════════════════════════
# 全局状态
# ═══════════════════════════════════════════════════════════════

_config = None
_agent = None
_workspace = ""


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
    resp = await send_from_directory(str(static_dir), "index.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# ── 文件浏览 API ──

@app.route("/api/files")
async def api_list_files():
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
        return jsonify({"path": path, "name": target.name, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Agent 配置 API ──

@app.route("/api/config")
async def api_config():
    global _config
    if _config is None:
        return jsonify({"status": "not_initialized"})
    models = []
    for m in _config.models:
        has_key = bool(m.get("api_key"))
        models.append({"name": m["name"], "provider": m.get("provider", ""), "has_key": has_key})
    return jsonify({
        "workspace": _workspace,
        "default_model": _config.default_model_name,
        "models": models,
    })

@app.route("/api/config/workspace", methods=["POST"])
async def api_set_workspace():
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
    data = await request.get_json(force=True)
    name = data.get("name", "")
    if not name:
        return jsonify({"error": "no model name"}), 400
    model_cfg = _config.find_model(name) if _config else None
    if not model_cfg:
        return jsonify({"error": f"model '{name}' not found"}), 404
    return jsonify(model_cfg)


# ── Agent 初始化 ──

@app.route("/api/init", methods=["POST"])
async def api_init_agent():
    global _agent, _config, _workspace
    from ..config import Config
    from ..model import ModelAdapter
    from ..cost import CostTracker
    from ..tools import ToolExecutor
    from ..agent import Agent

    data = await request.get_json(force=True) or {}
    if _config is None:
        _config = Config()
    workspace = data.get("workspace", _workspace or _config.workspace)
    _workspace = workspace
    _config._workspace_override = workspace

    model_name = data.get("model", "deepseek-v4-flash")
    api_key = data.get("api_key", "")
    model_config = _config.find_model(model_name) or {
        "name": model_name, "provider": "DeepSeek", "model": model_name,
    }
    if api_key:
        model_config["api_key"] = api_key
    elif not model_config.get("api_key"):
        model_config["api_key"] = _config.api_keys.get(model_config.get("provider", ""), "")
    if not model_config.get("api_key"):
        return jsonify({"error": "API Key not configured"}), 400

    model = ModelAdapter(model_config)
    cost_tracker = CostTracker(_config.pricing_dict)
    tools = ToolExecutor(workspace_dir=workspace)
    tools._web_mode = True

    from ..pricing_fetcher import fetch_pricing
    prices, _ = fetch_pricing(model_config["name"], model_config.get("provider", ""))
    if prices:
        cost_tracker.set_pricing(model_config["name"], prices)
        api_model = model_config.get("model", "deepseek-v4-flash")
        if api_model != model_config["name"]:
            cost_tracker.set_pricing(api_model, prices)

    ws_prompt = _config.system_prompt + (
        f"\n\nCurrent working directory: {workspace}\n"
        f"All file paths in tool results are relative to this directory.\n"
        f"\nCRITICAL - Interactive Programs:\n"
        f"NEVER run interactive programs directly (scripts with input(), "
        f"while True loops, python -i, node REPL). They will hang forever.\n"
        f"Instead, just OUTPUT the command using the bash tool (which creates "
        f"a command card). The user will see a '在新终端中执行' button on the "
        f"card and click it to run the command in a real terminal.\n"
        f"\nExample output for interactive.py:\n"
        f"  $ python interactive.py\n"
        f"  (Then tell user: click '在新终端中执行' button above to interact)\n"
    )

    _agent = Agent(
        model=model,
        cost_tracker=cost_tracker,
        tools=tools,
        system_prompt=ws_prompt,
        hooks=[],
    )
    _scan_workspace_tree()
    return jsonify({"ok": True, "workspace": workspace, "model": model_name})


# ── API: Agent 命令 ──

@app.route("/api/agent/command", methods=["POST"])
async def api_agent_command():
    global _agent
    data = await request.get_json(force=True)
    cmd = data.get("command", "").lower()
    if cmd == "reset":
        if _agent:
            _agent.reset()
        return jsonify({"ok": True, "response": "对话已重置"})
    elif cmd == "cost":
        if _agent:
            return jsonify({"ok": True, "response": _agent.get_session_summary()})
        return jsonify({"ok": True, "response": "未初始化"})
    else:
        return jsonify({"error": f"unknown command: {cmd}"}), 400


# ═══════════════════════════════════════════════════════════════
# SSE — AI 对话事件流 /api/chat (替代 WS)
# ═══════════════════════════════════════════════════════════════

_agent_lock = threading.Lock()


@app.route("/api/chat", methods=["POST"])
async def api_chat():
    """AI 对话 SSE 端点

    客户端 POST 消息，服务端返回 SSE 事件流：
      data: {"type":"thinking","content":"..."}
      data: {"type":"tool_call","name":"bash","args":{...}}
      data: {"type":"tool_result","name":"bash","result":"..."}
      data: {"type":"response","content":"..."}
      data: {"type":"summary","content":"..."}
      data: {"type":"error","content":"..."}
      data: {"type":"done"}
    """
    global _agent
    data = await request.get_json(force=True)
    text = (data.get("message") or data.get("msg", "")).strip()
    if not text:
        return jsonify({"error": "no message"}), 400
    if _agent is None:
        return jsonify({"error": "agent not initialized"}), 400

    # 线程安全队列：agent 线程放事件，SSE 生成器取事件
    q = queue_mod.Queue()

    def _push(event_type: str, **kw):
        q.put({"type": event_type, **kw})

    def _run_agent_sse():
        """在 executor 线程中运行 agent，事件推入队列"""
        # 创建 SSE 钩子
        hook = _SseHook(_push)
        _agent.hooks = [hook]
        try:
            with _agent_lock:
                _agent.run(text)
            _push("summary", content=_agent.get_session_summary())
        except Exception as e:
            _push("error", content=str(e))
        finally:
            _push("done")

    asyncio.get_event_loop().run_in_executor(None, _run_agent_sse)

    async def generate():
        while True:
            try:
                event = await asyncio.get_event_loop().run_in_executor(
                    None, q.get, True, 0.1
                )
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("type") == "done":
                    break
            except queue_mod.Empty:
                continue

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class _SseHook:
    """SSE 钩子：把 agent 事件推入 threading.Queue"""
    def __init__(self, push):
        self._push = push
    def on_llm_start(self, *a): pass
    def on_llm_end(self, usage, cost_info, iteration, model=""):
        total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        cost = cost_info.get("cost", 0)
        hit = usage.get("cache_hit_tokens", 0)
        inp = usage.get("input_tokens", 0)
        self._push("llm_end", model=model, tokens=total, input_tokens=inp,
                    output_tokens=usage.get("output_tokens", 0),
                    cache_hit_tokens=hit,
                    cache_pct=round(100 * hit / inp, 0) if inp and hit else 0,
                    cost=cost)
    def on_tool_start(self, name, args):
        self._push("tool_call", name=name, args=args)
    def on_tool_end(self, name, result, args=None):
        self._push("tool_result", name=name, result=result[:3000], args=args or {})
    def on_tool_chain_end(self, *a): self._push("tool_chain_end")
    def on_thinking(self, content): self._push("thinking", content=content)
    def on_response(self, content, usage_line):
        self._push("response", content=content)


# ── 工作区文件树 ──

_tree_cache: dict = {}
_tree_cache_lock = threading.RLock()

def _scan_workspace_tree():
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
                children.append({"name": entry.name, "path": rel, "is_dir": False})
        return {"name": path.name, "path": "", "is_dir": True, "children": children}
    with _tree_cache_lock:
        _tree_cache = _build_tree(base)

@app.route("/api/tree")
async def api_file_tree():
    # 每次请求直接重新扫描，避免缓存时序问题
    _scan_workspace_tree()
    with _tree_cache_lock:
        return jsonify(_tree_cache)


# ── 实时文件监控 ──

_file_watcher_started = False

def _start_file_watcher(workspace: str):
    """启动 watchfiles 后台线程，文件变化时自动刷新文件树缓存（防抖 1s）"""
    global _file_watcher_started
    if _file_watcher_started:
        return
    _file_watcher_started = True
    try:
        from watchfiles import watch
    except ImportError:
        return

    def _watcher_loop():
        last_scan = 0
        try:
            for _ in watch(workspace, recursive=True):
                now = time.time()
                if now - last_scan > 1.0:  # 防抖 1 秒
                    last_scan = now
                    _scan_workspace_tree()
        except Exception:
            pass

    t = threading.Thread(target=_watcher_loop, daemon=True)
    t.start()



# ═══════════════════════════════════════════════════════════════
# API — 查询可用 shell 类型
# ═══════════════════════════════════════════════════════════════

@app.route("/api/shells")
async def api_available_shells():
    from .terminal import detect_available_shells, SHELL_LABELS
    available = detect_available_shells()
    shells = []
    for key, label in SHELL_LABELS.items():
        shells.append({"key": key, "label": label, "available": available.get(key, False)})
    return jsonify(shells)

# ═══════════════════════════════════════════════════════════════
# WebSocket — PTY 终端通道 /ws/pty/<term_id> (仅 PTY)
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws/pty/<term_id>")
async def ws_pty(term_id: str):
    import asyncio
    import threading
    from urllib.parse import urlparse, parse_qs
    try:
        # 从WebSocket URL中解析查询参数（shell类型）
        query_params = parse_qs(urlparse(websocket.url).query)
        shell = query_params.get('shell', ['ps'])[0]
        print(f"  [PTY] WebSocket 连接请求: term_id={term_id}, shell={shell}, workspace={_workspace}")
        # 检查工作区是否设置
        if not _workspace:
            print(f"  [PTY] 错误: 工作区未初始化")
            try:
                await websocket.send(json.dumps({
                    "type": "error",
                    "msg": "工作区未初始化，请先完成初始化设置"
                }))
            except Exception:
                pass
            return
        
        term = _terminal_manager.get(term_id)
        if not term:
            print(f"  [PTY] 创建终端 {term_id}, shell={shell}")
            try:
                term = _terminal_manager.create(term_id, cwd=_workspace, shell=shell)
                print(f"  [PTY] 终端创建成功: alive={term.is_alive()}")
            except Exception as e:
                print(f"  [PTY] 终端创建失败: {e}")
                import traceback
                traceback.print_exc()
                try:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "msg": f"终端创建失败: {str(e)}"
                    }))
                except Exception:
                    pass
                return
        
        if not term.is_alive():
            print(f"  [PTY] 终端未激活")
            try:
                await websocket.send(json.dumps({
                    "type": "error",
                    "msg": f"终端启动失败，请确保已安装 pywinpty/winpty（pip install pywinpty）"
                }))
            except Exception:
                pass
            return
        
        print(f"  [PTY] 终端已激活，开始数据流传输")
        loop = asyncio.get_event_loop()
        stop_event = threading.Event()
        @copy_current_websocket_context
        async def pty_send(data: bytes):
            await websocket.send(data)
        def pty_reader():
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
        reader_thread = threading.Thread(target=pty_reader, daemon=True, name=f"pty-read-{term_id}")
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
                        elif cmd.get("type") == "destroy":
                            print(f"  [PTY] 收到销毁指令，清理终端 {term_id}")
                            _terminal_manager.destroy(term_id)
                            break
                        continue
                    except json.JSONDecodeError:
                        pass
                    term.write(msg.encode("utf-8"))
        except Exception as e:
            print(f"  [PTY] WebSocket 通信异常: {e}")
        finally:
            print(f"  [PTY] 关闭连接 {term_id}")
            stop_event.set()
            # 注意：不再自动销毁终端，由前端发送 type:"destroy" 消息控制
            # 这样终端切换标签时 WS 断开后会话保持，关闭标签时才销毁
    except Exception as e:
        print(f"  [PTY] WebSocket 处理异常: {e}")
        import traceback
        traceback.print_exc()


# ═══════════════════════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════════════════════

def start_server(config, host: str = "127.0.0.1", port: int = 8321,
                  open_browser: bool = True):
    global _config, _workspace, _tree_cache
    _config = config
    _workspace = config.workspace
    _scan_workspace_tree()
    _start_file_watcher(_workspace)
    url = f"http://{host}:{port}"
    print(f"\n  [FlyPig Web UI] 启动服务器...")
    print(f"  [SSE + PTY WS] {url}")
    print(f"  [工作区] {_workspace}")
    print()
    if open_browser:
        webbrowser.open(url)
    import hypercorn.asyncio
    import hypercorn.config as hcfg
    hconfig = hcfg.Config()
    hconfig.bind = [f"{host}:{port}"]
    hconfig.use_reloader = False
    try:
        asyncio.run(hypercorn.asyncio.serve(app, hconfig))
    except KeyboardInterrupt:
        print("\n  [FlyPig] 服务器已停止")
