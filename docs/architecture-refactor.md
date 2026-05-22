# FlyPig Agent 架构文档

> 最后更新: 2026-05-22 · 架构版本: v3 (Quart + SSE + WebSocket)

---

## 一、架构演进

```
v1: Textual TUI (终端界面)          → 纯 CLI，功能有限
v2: Flask + Vue 3 + SocketIO       → Web UI，双端口 (HTTP:8321 + WS:8322)
v3: Quart + SSE + WebSocket (当前)  → 单端口统一，原生 WebSocket 支持
```

### 各版本关键变化

| 版本 | Web 框架 | 终端通道 | Agent 事件 | 端口 |
|------|---------|---------|-----------|------|
| v1 | 无 | OS 原生 PTY | N/A | CLI |
| v2 | Flask | Flask-SocketIO (WS:8322) | SocketIO | 8321(HTTP) + 8322(WS) |
| v3 | Quart | 原生 WebSocket (同端口) | SSE | 8321 (单端口) |

---

## 二、整体架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                    flypig/__main__.py                             │
│          --web (默认)  /  --task /  -t  /  --no-web               │
└─────────────────────────┬────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────┐
│                    Quart 服务器 (hypercorn)                        │
│                        127.0.0.1:8321                            │
│                                                                   │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────────────┐ │
│  │  HTTP API   │   │  SSE 端点     │   │  WebSocket 端点        │ │
│  │  /api/*     │   │  /api/chat   │   │  /ws/pty/<term_id>    │ │
│  │             │   │              │   │                       │ │
│  │ - 配置/初始化│   │ Agent 事件流  │   │ PTY 字节管道           │ │
│  │ - 文件操作   │   │ Queue桥接     │   │ 读线程 + WS 写        │ │
│  │ - 文件树     │   │ SSE 格式     │   │ binary/JSON 消息      │ │
│  │ - Agent命令  │   │              │   │                       │ │
│  └──────┬──────┘   └──────┬───────┘   └──────────┬────────────┘ │
│         │                │                       │               │
│         └──────┬─────────┘                       │               │
│                │                                 │               │
└────────────────┼─────────────────────────────────┼───────────────┘
                 │                                 │
    ┌────────────▼────────┐           ┌────────────▼───────────┐
    │   Agent 线程池        │           │   PTY 读取线程          │
    │   (executor)         │           │   (threading.Thread)   │
    │                      │           │                        │
    │  Agent.run()         │           │  term.read() → WS.send │
    │  → EventHook → Queue │           │  (10ms polling loop)   │
    └──────────────────────┘           └────────────────────────┘
                          │
    ┌─────────────────────▼─────────────────────────────────────┐
    │                     前端 (Vue 3 SPA)                       │
    │                                                           │
    │  ┌─────────┬─────────────────────────┬──────────────────┐ │
    │  │ Sidebar │      Center              │     Chat         │ │
    │  │ 260px   │  (flex:1)               │     360px        │ │
    │  │         │                         │                  │ │
    │  │ 文件树   │  标签页 + CodeMirror     │  消息列表         │ │
    │  │ (递归)  │  (语法高亮, 只读)        │  (Markdown渲染)  │ │
    │  │         ├─────────────────────────┤  输入框           │ │
    │  │         │  xterm.js 终端面板       │  模型选择         │ │
    │  │         │  WebSocket ↔ PTY        │  SSE 事件流       │ │
    │  └─────────┴─────────────────────────┴──────────────────┘ │
    └───────────────────────────────────────────────────────────┘
```

---

## 三、模块详解

### 3.1 入口 (`__main__.py`)

```python
python -m flypig [--web | --task <msg> | --no-web]
```

- **`--web`** (默认): 启动 Quart Web 服务器，打开浏览器
- **`--task / -t`**: Headless 模式，执行一次性任务后退出
- **`--no-web`**: 经典 CLI 模式（Textual TUI）

### 3.2 Web 服务器 (`flypig/web/server.py`)

#### 技术栈

- **框架**: Quart (Flask 的 ASGI 版本)
- **ASGI 服务器**: Hypercorn
- **WebSocket**: 原生 `@app.websocket` (无需 Flask-SocketIO)
- **静态文件**: Quart 原生 `send_from_directory`
- **SSE**: `text/event-stream` + `Response(headers={"Content-Type": "text/event-stream"})`

#### API 路由一览

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回 SPA (index.html) |
| `/api/config` | GET | 获取配置、模型列表 |
| `/api/config/workspace` | POST | 设置/验证工作区路径 |
| `/api/config/apikey` | POST | 保存 API Key |
| `/api/init` | POST | 初始化 Agent 实例 |
| `/api/tree` | GET | 获取工作区文件树 |
| `/api/file` | GET | 读取文件内容 |
| `/api/files` | GET | 浏览目录 (带.gitignore排除) |
| `/api/agent/command` | POST | 发送 Agent 命令 (reset/cost) |
| `/api/chat` | POST | SSE 端点 - AI 对话流 |
| `/ws/pty/<term_id>` | WS | PTY 终端 WebSocket |

### 3.3 SSE 事件系统

**背景**: 最初使用 WebSocket 传输 Agent 事件，遇到 Windows 跨线程广播问题后重构为 SSE。

**架构**：

```
Agent 线程 (executor)
  │
  │  Agent 执行过程中产生事件 (thinking, tool_call, ...)
  ▼
_SseHook (EventHook 子类)
  │
  │  hook.push(event_type, **data) — 线程安全
  ▼
threading.Queue
  │
  │  asyncio.get_event_loop().run_in_executor(None, _sse_reader, queue)
  ▼
_sse_reader 协程
  │
  │  从 Queue 取出事件 → 写入 SSE Response body
  ▼
客户端 (fetch ReadableStream → SSE 解析)
```

**事件类型**:

| 事件 | 触发时机 | 前端显示 |
|------|---------|---------|
| `thinking` | AI 开始思考 | 省略号 |
| `tool_call` | AI 调用工具 | 工具名+参数摘要 |
| `tool_result` | 工具执行完毕 | 结果(截断300字) |
| `tool_chain_end` | 工具链结束 | tokens 统计 |
| `response` | AI 最终回复 | Markdown 渲染 |
| `summary` | 对话摘要 | 摘要内容 |
| `llm_end` | LLM API 调用结束 | tokens/费用/缓存命中 |
| `error` | 执行出错 | 红色错误提示 |
| `done` | 执行完毕 | 状态恢复 |

### 3.4 PTY 终端系统

**架构：独立 WebSocket 通道，仅用于 PTY，与 Agent 事件完全分离。**

```
xterm.js (浏览器)
  │  WebSocket 连接
  │  /ws/pty/t-1716358800123
  ▼
Quart @app.websocket("/ws/pty/<term_id>")
  │
  │  term = TerminalManager.get_or_create(term_id, cwd)
  │  启动 pty_reader 线程
  │
  ├── 接收方向: 浏览器键盘输入 → WS → term.write()
  │
  └── 发送方向: term.read() → pty_reader 线程 → asyncio.run_coroutine_threadsafe() → WS → xterm
```

#### 线程模型

```
┌─────────────────────────────────────────────────┐
│ async ws_pty(term_id)  (Quart 协程)              │
│                                                  │
│  while True:                                     │
│    msg = await websocket.receive()               │
│    if msg is bytes: term.write(msg)              │
│    if msg is str:                                │
│      if json → {type:"resize"}: term.resize()    │
│      else: term.write(msg.encode())              │
│                                                  │
│  ┌───────────── pty_reader (daemon thread) ────┐ │
│  │  while term.is_alive():                      │ │
│  │    data = term.read(4096)                    │ │
│  │    if data:                                  │ │
│  │      run_coroutine_threadsafe(send, loop)    │ │
│  │    else: wait 10ms                           │ │
│  └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

#### 重连策略

- 自动重连最多 3 次，间隔 2 秒
- 超限后显示 "重连失败，请点击 ↺ 重试"
- 终端状态显示在标题栏：`● 已连接` / `○ 连接中...` / `● 连接失败`

### 3.5 终端管理器 (`flypig/web/terminal.py`)

**Terminal 类** — 单个 PTY 终端封装

| 方法 | 说明 |
|------|------|
| `create()` | 启动 PTY shell 进程 |
| `read(size)` | 从 PTY 读取输出 (bytes / None / b"") |
| `write(data)` | 写入 PTY stdin |
| `resize(cols, rows)` | 调整终端尺寸 |
| `destroy()` | 终止进程、清理资源 |
| `is_alive()` | 进程是否存活 |

**跨平台实现**:

| 平台 | 库/方法 | Shell |
|------|--------|-------|
| Windows | `pywinpty` / `winpty` (自动检测) | `powershell.exe -NoProfile -NoLogo` |
| Linux/macOS | `pty.fork()` + `os.read/write` | `$SHELL` 或 `/bin/bash` |

**TerminalManager 类** — 线程安全的管理器

- 内部使用 `threading.Lock` 保护 `dict[str, Terminal]`
- 提供 `create/get/destroy/list/count/cleanup_all` 方法
- 所有终端在 WebSocket 断开时自动销毁

---

## 四、前端架构

### 4.1 技术栈

| 组件 | 用途 | 加载方式 |
|------|------|---------|
| Vue 3 (CDN) | 响应式 UI 框架 | `<script src="cdn">` |
| CodeMirror 5 | 代码编辑器 (只读) | CDN + 多 mode |
| xterm.js 5.3 | 终端模拟器 | CDN |
| xterm-addon-fit | 终端自适应 | CDN |
| marked.js | Markdown 渲染 | CDN |

### 4.2 终端前端实现

核心函数位于 `index.html`：

```javascript
// 终端状态变量
let _ptyWs = null;              // WebSocket 连接
let _ptyReconnectCount = 0;     // 重连计数器(上限3)
let _ptyTermId = '';            // 当前终端ID
let _xterm = null;              // xterm.js 实例
let _xtermFit = null;           // FitAddon 实例

// 关键函数
initTerminal()      // 创建 xterm + 建立 WS 连接
_connectPtyWs(id)   // WS 生命周期管理 + 重连
resetTerminal()     // 销毁重建
toggleTerminal()    // 折叠/展开
```

### 4.3 SSE 前端处理

```javascript
// 使用 fetch ReadableStream 解析 SSE
const res = await fetch('/api/chat', { method:'POST', body:{message} });
const reader = res.body.getReader();
while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  // 解析 data: {json} 行
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      handleEvent(data);
    }
  }
}
```

---

## 五、关键设计决策

### 5.1 Quart 替代 Flask

**理由**:
- Flask 不支持原生 WebSocket，需要 Flask-SocketIO 或 gevent-websocket
- Quart 是 Flask 的 ASGI 版本，API 兼容，原生支持 WebSocket
- ASGI 服务器 (Hypercorn/Uvicorn) 比 WSGI 更适合长连接场景

**代价**:
- 部分 Flask 扩展不兼容 Quart (如 Flask-CORS)
- Quart 文档不如 Flask 完善

### 5.2 SSE 替代 WebSocket (for Agent)

**理由**:
- Windows 下 `call_soon_threadsafe` + `async def` 广播导致协程被静默丢弃 (pitfall #12)
- SSE 是单向 HTTP 流，天然适合 server→client 事件推送
- 使用 `threading.Queue` 桥接线程和异步，数据流清晰
- 前端用标准 `fetch` API，不需额外库

**代价**:
- 单向通道，客户端不能通过同一连接发消息（但 Agent 通过 POST 发消息，不冲突）
- 长连接在代理服务器可能超时

### 5.3 Dual-Path 终端

**理由**: Docker Sandbox (Agent 命令) 和 PTY (用户交互) 分离，避免编码/控制序列兼容性问题。

详见 `docs/terminal-interaction.md`。

---

## 六、数据流

### 6.1 AI 对话流程

```
用户输入 → POST /api/chat → SSE stream
                                  │
                                  ▼
                      _agent.run(user_input)
                                  │
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
      LLM API 调用          工具执行             事件分发
      (ModelAdapter)    (ToolExecutor)       (_SseHook → Queue)
            │                     │                     │
            ▼                     ▼                     ▼
      提 token/费用         bash/file操作         → SSE 响应体
      更新 CostTracker      subprocess/code
                                  │
                                  ▼
                           对话结束 → SSE "done" 事件
```

### 6.2 终端 I/O 流程

```
键盘输入 → xterm.onData → WS.send(text) → Quart WS handler → term.write() → PTY stdin
PTY stdout → term.read() → pty_reader 线程 → run_coroutine_threadsafe → WS.send(binary) → xterm.write()
```

---

## 七、文件结构

```
flypig/
├── __init__.py
├── __main__.py          # 入口点
├── agent.py             # Agent 核心 (自愈机制)
├── background.py        # 后台任务
├── cli.py               # CLI 界面
├── config.py            # 配置管理
├── config.yaml          # 配置文件
├── cost.py              # 费用统计
├── hooks.py             # 事件钩子系统
├── model.py             # 模型适配器
├── model_registry.py    # 模型注册表
├── pricing_cache.json   # 定价缓存
├── pricing_fetcher.py   # 定价抓取
├── tools.py             # 工具执行器
└── web/
    ├── __init__.py
    ├── server.py         # Web 服务器 (Quart)
    ├── terminal.py       # PTY 终端管理
    └── static/
        └── index.html    # 前端 SPA (Vue 3)
docs/
├── architecture-refactor.md   # ← 本文档
├── hooks.md                   # Hook 系统设计
├── peer-reference.md          # 友商分析
├── pitfall.md                 # PTY/SSE 踩坑记录
├── pitfalls.md                # 历史踩坑记录
├── prd.md                     # PRD
├── README.md                  # 项目 README
├── requirement.md             # 需求清单
├── roadmap.md                 # 路线图
├── sandbox_plan.md            # Docker 沙箱方案
├── terminal-interaction.md    # 终端交互设计
└── toolchain-self-heal.md     # 工具链自愈
```

---

## 八、运行时要求

| 依赖 | 用途 | 安装方式 |
|------|------|---------|
| Quart | ASGI Web 框架 | `pip install quart` |
| Hypercorn | ASGI 服务器 | `pip install hypercorn` |
| pywinpty (Windows) | PTY 终端 | `pip install pywinpty` |
| Vue 3 | 前端框架 | CDN |
| xterm.js | 终端模拟 | CDN |
| CodeMirror | 代码编辑器 | CDN |
