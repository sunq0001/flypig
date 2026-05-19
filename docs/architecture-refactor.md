# FlyPig 架构重构设计文档

> 基于原生 WebSocket(asyncio) + PTY 的终端系统（AI 事件保持 SSE）

## 一、架构总览

### 现状问题

当前 Flask-SocketIO + SSE 双通道架构存在两个根本问题：

1. **SocketIO 不适合终端**：终端交互本质是字节流（PTY 原始输出含 ANSI 码、二进制帧），SocketIO 只能传字符串/JSON，需要额外序列化
2. **gevent 污染**：`monkey_patch_all()` 影响 subprocess/threading 行为，导致不可预期的问题

注意：**当前 SSE 用于 AI 事件推送是合理且隔离的**，不在改造范围内。

### 新架构：双服务器，三通道

```
┌──────────────────────────────────────────────────────────────┐
│                         浏览器                                    │
│                                                                   │
│  ┌── 终端面板 ──────────────────────────────────────┐          │
│  │  Tab 1 (人: 可交互)         Tab N (AI: 只读)       │          │
│  │  ┌────────────────────┐    ┌──────────────────┐   │          │
│  │  │ xterm.js ↔ PTY    │    │ xterm.js (只读)  │   │          │
│  │  │ 双向实时字节流     │    │ 展示卡片命令结果  │   │          │
│  │  └────────┬───────────┘    └──────────────────┘   │          │
│  └───────────┼───────────────────────────────────────┘          │
│              │                                                   │
│  ┌── 对话区 ─┼──────────────────────────────────────────────┐   │
│  │           │                                                   │   │
│  │  💬 用户发消息 ──→ POST /api/run ──→ Agent 线程              │   │
│  │           │  Agent 执行 subprocess  ↔ LLM                    │   │
│  │           │  输出 → WebEventHook → SSE → 卡片               │   │
│  │           │                                                    │   │
│  │  ┌── 命令卡片 ──────────────────────────────┐               │   │
│  │  │  💻 npm install                           │               │   │
│  │  │  added 152 packages...                    │               │   │
│  │  │  [📋复制] [▶在终端打开] [↺重试]          │               │   │
│  │  └───────────────────────────────────────────┘               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
  |  WS(字节)    |      SSE推送          |      HTTP REST
  |  port 8322   |      port 8321        |      port 8321
  ▼              ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    服务器 (双进程并行)                             │
│                                                                   │
│  Port 8321: Flask HTTP (threading, 无 gevent, 无 monkey_patch)    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  /api/config    /api/run    /api/files    /api/tree         │  │
│  │  SSE: /api/events (WebEventHook → Queue)                    │  │
│  │  Agent 线程: agent.run() → tool_bash → subprocess           │  │
│  │  └─ 结果推 SSE → 前端卡片 + 返回 AI 决策                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Port 8322: asyncio WebSocket 服务器 (纯 PTY 管道)                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  /pty/:id        双向字节 ↔ PTY（新, 替换 SocketIO）        │  │
│  │  TerminalManager (线程安全, asyncio 层)                     │  │
│  │  └─ PTY-1: {proc, fd, alive}                               │  │
│  │  └─ PTY-2: {proc, fd, alive}                               │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 关键原则

- **服务器不解析、不记账、不检测标记** — 仅仅是字节管道
- **PTY 和 AI 事件完全隔离** — 不同协议、不同端口、不同进程
- **AI 命令走 subprocess，不走 PTY** — 结果推卡片给人看 + 返回给 AI
- **两个服务器共享最少状态** — 仅一个线程安全的终端列表做管理用

## 二、三通道详细设计

### 通道 1：PTY 终端（WebSocket，原始字节）

**用途**：人操作交互式终端

**端口**：8322

**路径**：`ws://host:8322/pty/{term_id}`

**方向**：双向

**格式**：原始二进制帧（`Uint8Array`）

| 方向 | 内容 | 说明 |
|:----:|------|------|
| 客户端→服务器 | 键盘按键字节 | 每次按键（含 Ctrl+C = `\x03`） |
| 服务器→客户端 | PTY stdout 输出 | Shell 输出（含 ANSI 颜色码） |
| 服务器→客户端 | 调整大小通知 | `{type:"resize", cols, rows}` 以文本帧发送 |

**服务器逻辑**（极简管道）：

```
ws.onmessage → os.write(ptm_fd, data)          # 按键 → PTY
pty 输出 → asyncio 事件循环轮询                 # PTY → xterm.js
         → ws.send(output_bytes)
```

**生命周期**：
```
WS 连接建立 → 创建 PTY + Shell → 双向转发字节
WS 断开 → 杀死 Shell 进程 → 清理 PTY
```

### 通道 2：AI 事件推送（SSE）

**用途**：Agent 思考/工具执行/结果的单向推送（服务器 → 客户端）

**端口**：8321

**路径**：`/api/events`

**格式**：SSE (Server-Sent Events)

**状态**：**保留不动**。当前 `WebEventHook` + `Queue` + SSE 工作正常。

### 通道 3：HTTP REST API

**用途**：配置、初始化、文件操作、用户发消息

**端口**：8321

**路径**：`/api/*`

**状态**：**保留不动**。现有路由正常。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 静态页面 |
| GET | `/api/config` | 配置信息 |
| POST | `/api/init` | 初始化 Agent |
| POST | `/api/run` | 运行 Agent（发送消息） |
| POST | `/api/config/workspace` | 设置工作区 |
| POST | `/api/config/apikey` | 设置 API Key |
| POST | `/api/config/select-model` | 选择模型 |
| GET | `/api/files?path=...` | 文件列表 |
| GET | `/api/file?path=...` | 文件内容 |
| GET | `/api/tree` | 目录树 |

## 三、WebSocket 服务器设计（asyncio）

### 技术选型

| 组件 | 选择 | 理由 |
|:----|:----|:----|
| WebSocket 库 | `websockets` | 成熟稳定，纯 asyncio |
| 事件循环 | `asyncio` | 天然适合 PTY I/O |
| PTY (Unix) | `pty` 标准库 | 内置，无依赖 |
| PTY (Windows) | `pywinpty` | 唯一的 Win PTY 方案 |
| 并行启动 | `threading` | 与 Flask 同时在 tread 中启动 asyncio 事件循环 |

### 启动方式

```python
# server.py
import asyncio, threading
import websockets

async def ws_handler(websocket):
    path = websocket.path  # /pty/{term_id}
    await handle_pty(websocket, path)

def start_ws_server(host, port):
    """在新线程中启动 asyncio WebSocket 服务器"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        websockets.serve(ws_handler, host, port)
    )
    loop.run_forever()

# 同时启动
threading.Thread(target=start_ws_server, args=(host, 8322), daemon=True).start()
socketio.run(app, host=host, port=8321)  # 或直接 app.run()
```

### PTY Handler

```python
async def handle_pty(websocket):
    term_id = websocket.path.split("/pty/")[1]
    term = terminal_manager.create(term_id)
    
    async def read_pty():
        """异步轮询 PTY 输出 → WS"""
        loop = asyncio.get_event_loop()
        while True:
            data = await loop.run_in_executor(
                None, os.read, term.pty_fd, 4096
            )
            if not data:
                break
            await websocket.send(data)
    
    async def write_pty():
        """WS 消息 → PTY stdin"""
        async for message in websocket:
            if isinstance(message, bytes):
                os.write(term.pty_fd, message)
            else:
                cmd = json.loads(message)
                if cmd.get("type") == "resize":
                    term.resize(cmd["cols"], cmd["rows"])
    
    try:
        await asyncio.gather(read_pty(), write_pty())
    finally:
        terminal_manager.destroy(term_id)
```

### TerminalManager

```python
class TerminalManager:
    _lock: threading.Lock
    _terminals: dict[str, Terminal]
    
    def create(term_id) -> Terminal    # 创建 PTY + Shell
    def destroy(term_id)               # 关闭 PTY
    def get(term_id) -> Terminal       # 获取终端
    def list() -> list[dict]           # 列出所有终端
```

### Terminal 对象

```python
class Terminal:
    term_id: str
    pty_fd: int                  # PTY master fd
    process: subprocess.Popen    # Shell 进程
    shell_name: str              # "PowerShell" | "bash"
    created_at: float
    ws: WebSocket | None         # 绑定的 WebSocket 连接
```

## 四、AI 命令执行（保留不动）

AI 不经过 PTY。当前流程不变：

```
用户消息 → POST /api/run → agent.run()
  → tool_bash → subprocess.Popen(shell=True)     [原有 _run_inline]
  → 逐行读取 → WebEventHook._broadcast() → SSE
  → 前端渲染卡片（命令、实时输出、结果）
  → 完整输出返回 AI 做下一步决策
```

### "在终端打开"功能

```
点击卡片 ▶ 按钮
  → 前端创建新 Tab（本地 xterm.js，只读模式，不连 WS/PTY）
  → 把卡片命令 + 输出写入 xterm 显示
  → 不可输入，仅查看
```

## 五、前端改动

### WebSocket 连接

```javascript
// PTY 终端：ws://host:8322/pty/{termId}
const ptyWs = new WebSocket(`ws://${host}:8322/pty/${termId}`);
ptyWs.binaryType = 'arraybuffer';

ptyWs.onopen = () => { /* 终端就绪 */ };
ptyWs.onmessage = (e) => term.write(new Uint8Array(e.data));
ptyWs.onclose = () => setTimeout(reconnect, 2000);

// xterm.js 按键 → WS
term.onData(data => ptyWs.send(data));
term.onResize(({ cols, rows }) =>
    ptyWs.send(JSON.stringify({ type: 'resize', cols, rows }))
);
```

### SSE 保留不动

```javascript
// 现有 EventSource 代码，不需要改
const evtSource = new EventSource('/api/events');
evtSource.addEventListener('tool_start', ...);
evtSource.addEventListener('tool_output', ...);
```

## 六、改动文件清单

| 文件 | 操作 | 说明 |
|------|:----:|------|
| `flypig/web/server.py` | 修改 | 移除 SocketIO，加 asyncio WS 启动，加 `start_pty_server` |
| `flypig/web/terminal.py` | 重写 | 移除 TerminalSession/TerminalManager（旧），新增 asyncio PTY Terminal + TerminalManager |
| `flypig/web/static/index.html` | 修改 | 替换 SocketIO 客户端代码为原生 WebSocket |
| `flypig/tools.py` | **不动** | _run_inline 已有回调机制 |
| `flypig/hooks.py` | **不动** | WebEventHook 推 SSE 正常 |
| `requirements.txt` | 更新 | 移除 flask-socketio, gevent；新增 websockets, pywinpty |

**不改的文件**：`config.py`, `agent.py`, `model.py`, `model_registry.py`, `cli.py`, `context_compressor.py`, `cost.py`, `sandbox.py`, `pricing_fetcher.py`

## 七、实施计划

### Phase 1: 环境准备
- [ ] 安装依赖（`pip install websockets pywinpty`）
- [ ] 移除依赖（`pip uninstall flask-socketio gevent`）
- [ ] 验证当前代码在干净分支（refactor-websocket）上可运行

### Phase 2: WebSocket PTY 服务器
- [ ] 实现 `Terminal` 类（PTY 创建/销毁）
- [ ] 实现 `TerminalManager`（线程安全列表）
- [ ] 实现 Windows PTY（pywinpty）
- [ ] 实现 Unix PTY（标准库 pty）
- [ ] 实现 asyncio WS handler（bytes ↔ PTY）
- [ ] 与 Flask 并行启动

### Phase 3: 删除 SocketIO
- [ ] 删除 server.py 中的 SocketIO 初始化
- [ ] 删除 terminal:start/input/output/resize 事件处理器
- [ ] 删除 socketio.run() 改用 app.run()
- [ ] 确认 SSE 不受影响

### Phase 4: 前端重构
- [ ] 移除 index.html 中的 SocketIO 客户端
- [ ] 实现原生 WebSocket 连接 + 重连
- [ ] xterm.js PTY 集成（字节通道）
- [ ] 多终端标签管理
- [ ] "在终端打开"只读 Tab 功能

### Phase 5: 清理与验证
- [ ] 删除无用 import 和代码
- [ ] 端到端功能测试（终端创建、输入、输出、Ctrl+C、多标签）
- [ ] AI 命令执行 + 卡片展示测试
- [ ] SSE 事件推送测试（thinking, tool_start/output/end）
