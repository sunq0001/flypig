---
name: native-websocket-architecture
overview: Quart (ASGI) 替代 Flask (WSGI)，单端口 8321 原生 WebSocket 支持。/ws/chat（AI 对话）+ /ws/pty/<id>（PTY 终端）。
todos:
  - id: deps
    content: pyproject.toml: flask+simple-websocket -> quart+hypercorn
    status: completed
  - id: hooks
    content: hooks.py: 新增 WsEventHook（run_coroutine_threadsafe 桥接 sync→async）
    status: completed
  - id: server
    content: server.py: Flask -> Quart，HTTP async + @app.websocket 端点
    status: completed
  - id: frontend
    content: index.html: EventSource -> WebSocket(/ws/chat)
    status: completed
---

## 核心问题

当前 FlyPig 的 Web UI 在 Flask (WSGI) 上强行挂载 WebSocket（simple-websocket），Werkzeug 3.x 在 HTTP handler 级别拦截 WebSocket Upgrade 请求，导致连接始终返回 400。根因是**选错了框架** — WSGI 不适合 WebSocket。

## 用户需求

- 用原生 WebSocket 替代 SSE + HTTP POST 的拼凑方案
- **AI 聊天** ↔ WebSocket 双向（用户发消息，AI 流式回复）
- **用户终端** ↔ WebSocket 双向（xterm.js + PTY bridge）
- **AI 终端** → Docker subprocess，结果在对话区显示为**可交互卡片**
- 卡片操作：复制命令、在用户终端打开、重试、中止
- 一个框架同时搞定 HTTP + WebSocket，单端口

## 核心功能

1. **框架迁移**: Flask → **Quart**（async Flask，原生 WebSocket 支持，单端口）
2. **AI 对话通道**: WebSocket `/ws/chat`（替代 SSE + HTTP POST）
3. **用户终端通道**: WebSocket `/ws/pty/<id>`（xterm.js + PTY）
4. **AI 执行卡片**: 对话区卡片显示命令和输出，支持交互操作
5. **HTTP API**: 保留静态文件 + 文件浏览 + 配置（请求-响应模式）
6. 移除所有 simple-websocket / flask-sock 依赖

## 技术栈

### 当前问题根因

- Flak (Werkzeug 3.x) 在 HTTP handler 层拦截 `Upgrade: websocket`
- `simple-websocket` 依赖 `environ['werkzeug.socket']`，Werkzeug 3.x 已移除
- 所有 WSGI+WebSocket 方案均为框架级 hack

### 选定方案

- **框架**: **Quart**（Flask 的 asyncio 版本，API 几乎一致）
- **服务器**: **Hypercorn**（Quart 的 ASGI 服务器，替代 waitress）
- **端口**: 单端口 8321，HTTP + WebSocket 在同一进程

### 完整架构

```
浏览器 (单端口 8321)           服务器 (Quart + Hypercorn)
  │
  ├── WS /ws/chat ────────── AI 对话通道
  │   ┌──────────────────────────────────────────┐
  │   │ 用户 → 服务端:                           │
  │   │   {"type":"chat","msg":"帮我装express"}   │
  │   │   {"type":"card_action","card_id":"x",   │
  │   │    "action":"retry|stop|open_terminal|   │
  │   │              copy_command"}              │
  │   │                                          │
  │   │ 服务端 → 用户:                           │
  │   │   {"type":"thinking","content":"..."}    │
  │   │   {"type":"tool_call","id":"x",          │
  │   │    "name":"bash","args":{"cmd":"..."}}   │
  │   │   {"type":"tool_result","id":"x",        │ ← 卡片数据
  │   │    "output":"added 50 packages",         │
  │   │    "status":"completed|failed"}          │
  │   │   {"type":"response","content":"..."}    │
  │   └──────────────────────────────────────────┘
  │
  ├── WS /ws/pty/<id> ────── 用户终端通道
  │   ┌──────────────────────────────────────────┐
  │   │ 键盘输入 (raw bytes)  → PTY stdin       │
  │   │ PTY stdout → xterm.js 渲染              │
  │   │ resize 事件 → PTY 窗口尺寸调整            │
  │   └──────────────────────────────────────────┘
  │
  └── HTTP /api/* ────────── 文件/配置 API
      ┌──────────────────────────────────────────┐
      │ GET  /           → index.html (SPA)      │
      │ GET  /api/tree   → 工作区文件树          │
      │ GET  /api/file   → 文件内容              │
      │ POST /api/init   → 初始化 Agent          │
      │ POST /api/config → 设置工作区/API Key    │
      └──────────────────────────────────────────┘

============================================================
内部数据流：
============================================================

Agent 执行命令 (与 WS 无关，纯 subprocess):

  Agent 调用 tool_bash("npm install express")
    │
    ▼
  Docker Sandbox (docker exec)
    │  subprocess.run(capture_output=True)  ← 阻塞等待
    │
    ▼
  结果 → EventHook.on_tool_end()
    │
    ▼
  Quart WebSocket → 发送到浏览器
    {"type":"tool_result","id":"card_1",
     "output":"added 50 packages",
     "command":"npm install express",
     "status":"completed"}
    │
    ▼
  前端渲染为可交互卡片

卡片交互 (用户操作):

  ┌──────────────────────────────────┐
  │ 🔧 npm install express          │ ← 命令
  │ ─────────────────────            │
  │ added 50 packages               │ ← 输出
  │ ─────────────────────            │
  │ [复制] [在终端打开] [重试] [中止] │ ← 操作按钮
  └──────────────────────────────────┘

  [复制]       → 写入剪贴板，前端本地操作
  [在终端打开]  → WS /ws/chat 发送:
                   {"type":"card_action",
                    "action":"open_in_terminal",
                    "card_id":"card_1"}
                   后端: PTY write("npm install express\r\n")
  [重试]       → WS /ws/chat 发送:
                   {"type":"card_action",
                    "action":"retry","card_id":"card_1"}
                   后端: 重新调用 tool_bash
  [中止]       → WS /ws/chat 发送:
                   {"type":"card_action",
                    "action":"stop","card_id":"card_1"}
                   后端: 终止 docker exec 进程
```

### async/sync 桥接

| 场景 | 方式 |
|------|------|
| Agent 事件 (sync) → WS send (async) | `EventHook` 中用 `asyncio.get_event_loop().call_soon_threadsafe()` |
| PTY read/write (sync) → 在 async handler 中调用 | `loop.run_in_executor(None, term.read, 4096)` |

### 目录结构

```
flypig/web/
├── __init__.py          # [UNCHANGED]
├── server.py            # [MODIFY] Flask → Quart，保持 HTTP API 逻辑
├── terminal.py          # [UNCHANGED] PTY 终端管理
└── static/
    └── index.html       # [MODIFY] SSE → WS /ws/chat，PTY WS /ws/pty

flypig/
├── __main__.py          # [MODIFY] Quart + Hypercorn 启动
├── hooks.py             # [MODIFY] 新增 WsEventHook 替代 WebEventHook
├── pyproject.toml       # [MODIFY] 依赖: quart + hypercorn

docs/
└── terminal-interaction.md  # [MODIFY] 更新架构
```

### 交互卡片数据模型

```python
@dataclass
class CommandCard:
    card_id: str
    command: str
    status: str  # running | completed | failed | cancelled
    output: str = ""
    exit_code: Optional[int] = None
```

### 依赖变更

| 移除　　　　　　　　　　　　　　　| 新增　　　　　　 |
| -----------------------------------| ------------------|
| flask, waitress, simple-websocket | quart, hypercorn |