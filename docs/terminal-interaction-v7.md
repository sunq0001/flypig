# AI-User-PTY 终端交互设计方案 v7

> 终稿汇总：演进历程、现状分析、v7 方案设计、关键技术决策
> 时间：2026-05-28

---

## 1. 背景与演进历程

### v1 — CLI 时代（初始版本）
- **实现**：AI 直接通过 subprocess 执行命令，捕获 stdout/stderr
- **问题**：无交互能力，无终端显示，用户只能看到干巴巴的文本结果
- **丢失**：无

### v2 — Web + SocketIO 时代
- **实现**：Flask + SocketIO 双工通道，xterm.js 前端终端，AI 用 tool_bash 执行
- **问题**：SocketIO 在 Windows 稳定性差；AI 命令与用户操作争抢同一终端

### v3 — Quart + SSE + WS 时代（当前架构）
- **实现**：
  - Quart (ASGI) 替代 Flask，单端口原生 WS
  - `/api/chat` SSE 端点承载 AI 对话事件流
  - `/ws/pty/<term_id>` 独立 WebSocket 通道连接 xterm.js
- **AI 命令注入机制**（当前）：
  - `_run_terminal_interactive()` → 注册 injection → push SSE → 返回 `[TERMINAL_INJECTED:msgId]`
  - AI 线程不等待，直接继续
  - 服务端 pty_reader 异步读 PTY 输出 → 追加到 buffer
  - 独立 SSE `/api/terminal-events` 实时推送 buffer 增量到前端
  - 用户观察终端后手动点击"推送终端结果" → 发送给 AI 分析

### 各版本方案文档演进

在 `.codebuddy/plans/` 中共有 6 份 PTY 相关方案文档：

| 文档 | 核心思路 | 状态 |
|------|---------|------|
| `restore-pty-terminal-frontend` | 恢复前端 xterm.js PTY 连接函数 | 未完成 |
| `服务端PTY监听_交互卡片确认` | 服务端 tap + marker 检测 + 前端轮询 + 交互卡片 | 未完成 |
| `服务端PTY输出监听改造` | 服务端 tap + marker + threading.Event.wait() | 未完成 |
| `全异步PTY交互_独立SSE推送` | 全异步 + 独立 SSE 端点实时推送 buffer | 已完成 |
| `SSE实时推送_用户决定分析时机` | 在 #4 基础上细化时序图 + 零 threading/锁/轮询 | 进行中 |
| `terminal-system-redesign` | SocketIO 统一通道 + 多终端标签 + 命令卡片 + CLI XML | 已完成 |

**核心演进脉络**：Flask → Quart → async；轮询 → SSE 推送；用户捕获 → 服务端 tap；AI 等待 → AI 不等待。

---

## 2. 当前实现分析

### 2.1 核心文件与职责

| 文件 | 职责 |
|------|------|
| `flypig/tools.py` | `_run_terminal_interactive()` — 注册注入、push SSE、返回 INJECTED |
| `flypig/agent.py` | `_execute_tool_call()` — 检测 INJECTED 直接透传，不阻塞 |
| `flypig/web/server.py` | `pty_reader` tap buffer、`/api/terminal-events` SSE 巡检、`/api/terminal/output` 输出获取 |
| `flypig/web/terminal.py` | `Terminal` / `TerminalManager` — PTY 进程管理 |
| `flypig/web/static/index.html` | 前端 xterm.js + inject-bind + 事件处理 |

### 2.2 当前数据流

```
AI 调用 tool_bash(command, persist=False)
  ↓
tool_bash() 检测 _web_mode + _terminal_push_fn
  ↓
_run_terminal_interactive(command, timeout_val)
  ├─ 生成 msgId (uuid)
  ├─ 注册 _terminal_injections[msgId] = {buffer, pty_term_id, command, consumed, truncated}
  ├─ push_fn("terminal_inject", msgId, command)  → 推送到 SSE 事件队列
  └─ 返回 "[TERMINAL_INJECTED:{msgId}]"
  ↓
agent.py _execute_tool_call() 检测到 INJECTED 前缀
  └─ 直接透传给 LLM (不等待)
  ↓
LLM 收到 tool_result，继续后续推理
      │
      │ [并行进行]
      ▼
前端 SSE 事件流收到 "terminal_inject"
  └─ 将命令写入当前 PTY 终端
  └─ POST /api/terminal/inject-bind/{msgId} 绑定 pty_term_id
  ↓
服务端 pty_reader:
  while term.is_alive():
    data = term.read(4096)
    if data:
      active_msg_id = _active_injections.get(term_id)
      _terminal_injections[active_msg_id].buffer.append(data)
      同时通过 WS 发送到 xterm.js 实时显示
  ↓
独立 SSE /api/terminal-events (每秒巡检):
  for each injection:
    if buffer 有增量 → push "terminal_output" 事件
      ↓
前端收到 terminal_output → 渲染到对话卡片
      ↓
用户点击 "推送终端结果"
  └─ GET /api/terminal/output/{msgId}
    └─ 合并 buffer bytes + strip_ansi + 标记 consumed
    └─ 返回 output text
      ↓
前端构造 message + 自动 POST /api/chat
      ↓
AI 分析终端输出
```

### 2.3 核心问题

1. **命令注入链路 7 步，每步都有时序问题**：
   AI → SSE → 前端 → API → 后端 → PTY → 终端
   任何一步延迟都导致输出丢失或绑定错位

2. **无命令完成检测**：
   没有 START/END marker，没有静默判断
   完全依赖用户主观判断"命令执行完了没"

3. **buffer 数据脏**：
   pty_reader 逐字节读取，buffer 包含大量 ANSI 序列、回显、prompt 提示符
   用户点击时 strip_ansi 后才推送，AI 看到的并非原始纯净输出

4. **用户必须手动点"推送"按钮**：
   非交互式命令（ls, git, pip）也强制用户操作
   打断自动工作流，尤其是多步链式任务时效率低

---

## 3. v7 方案设计

### 3.1 核心改进：三种命令模式

借鉴 Claude Code 的持久化 bash session + 自动回传思想，但结合我们 xterm.js 独立终端的特性，分三条路径：

| 场景 | 检测方式 | 回喂机制 | 用户操作 |
|------|---------|---------|---------|
| **① 有明确结束的命令**（git, pip, npm install） | `###AI_END###` marker | 自动回喂 | 无操作 |
| **② 耗时/持续输出命令**（服务器启动、编译） | 3 秒静默检测 | 自动回喂 | 无操作 |
| **③ 交互式命令**（vim, htop, ssh, python shell） | 无自动检测 | 用户点击"推送" | 必须手动触发 |

### 3.2 方案①：非交互式 + END 标记

```python
# tools.py _run_terminal_interactive() 修改
def _run_terminal_interactive(self, command: str, timeout_val: int, interactive: bool = False) -> str:
    import uuid
    msg_id = str(uuid.uuid4())
    injections = getattr(self, '_terminal_injections', {})

    # 非交互式：硬编码包装 START/END 标记
    wrapped_command = command
    if not interactive:
        wrapped_command = (
            f'echo "###AI_START###"\n'
            f'{command}\n'
            f'echo "###AI_END###"'
        )

    injections[msg_id] = {
        "buffer": [],
        "pty_term_id": None,
        "command": command,
        "interactive": interactive,   # 新增字段
        "consumed": False,
        "truncated": False,
        "completed": False,           # 命令是否完成
    }

    push_fn = getattr(self, '_terminal_push_fn', None)
    if push_fn:
        push_fn("terminal_inject", msgId=msg_id, command=wrapped_command,
                interactive=interactive)

    return f"[TERMINAL_INJECTED:{msg_id}]"
```

### 3.3 方案①/②：pty_reader 完成检测

```python
# server.py pty_reader 改造
import time

# 新增：静默检测配置
_SILENCE_THRESHOLD = 3.0  # 3 秒无输出视为完成

async def pty_reader():
    nonlocal reader_stopped
    last_output_time = time.time()
    marker_found = False
    marker_buffer = b""  # 用于检测跨包 marker

    while term.is_alive() and not reader_stopped:
        data = await asyncio.to_thread(term.read, 4096)
        if data is None:
            break
        if data:
            last_output_time = time.time()

            # 追加到注入 buffer（仅对非 consumed 的注入）
            active_msg_id = _active_injections.get(term_id)
            if active_msg_id:
                inj = _terminal_injections.get(active_msg_id)
                if inj and not inj.get("consumed"):
                    inj["buffer"].append(data)

                    # ── 完成检测：END 标记 ──
                    if not inj.get("interactive"):
                        marker_buffer += data
                        if b"###AI_END###" in marker_buffer:
                            marker_found = True
                            inj["completed"] = True
                            # 触发自动推送
                            await trigger_auto_push(active_msg_id)
                            marker_buffer = b""

            # 送 WS（实时显示到 xterm.js）
            try:
                ws_send_queue.put_nowait(data)
            except asyncio.QueueFull:
                pass
        else:
            # ── 完成检测：静默超时 ──
            now = time.time()
            if active_msg_id and not marker_found:
                inj = _terminal_injections.get(active_msg_id)
                if inj and not inj.get("interactive") and not inj.get("completed"):
                    if now - last_output_time > _SILENCE_THRESHOLD:
                        inj["completed"] = True
                        await trigger_auto_push(active_msg_id)
            await asyncio.sleep(0.01)

async def trigger_auto_push(msg_id):
    """自动推送终端输出给 AI"""
    inj = _terminal_injections.get(msg_id)
    if not inj or inj.get("consumed") or not inj.get("completed"):
        return

    # push terminal_complete 事件到前端 SSE
    # 前端收到后自动调 /api/terminal/output 获取输出 → 自动发 /api/chat
    _push("terminal_complete", msgId=msg_id)
```

### 3.4 方案③：交互式命令（保留用户按钮）

**自动判断交互式**：在 `tools.py` 中添加 `_guess_interactive()` 函数，避免依赖 AI 自觉。

```python
# tools.py 新增
_INTERACTIVE_COMMANDS = {
    'vim', 'vi', 'nano', 'emacs', 'htop', 'top', 'less', 'more',
    'mysql', 'psql', 'sqlite3', 'redis-cli',
    'python', 'python3', 'ipython', 'node', 'irb',  # REPL
    'ssh', 'telnet',
    'bash', 'zsh', 'sh',  # new shell
}

def _guess_interactive(command: str) -> bool:
    """根据命令名自动判断是否交互式"""
    first_word = command.strip().split()[0].lower()
    if first_word in _INTERACTIVE_COMMANDS:
        return True
    # 复合命令前缀
    if command.strip().startswith(('kubectl exec', 'docker exec -it')):
        return True
    return False
```

交互式命令注入时：
- 不包装 START/END 标记
- 不检测完成 / 不自动推送
- 前端显示常驻按钮"发送给 AI 分析"
- 终端标签显示 🔵 交互模式 标识

用户在终端中自由操作（vim 编辑、ssh 连接、htop 监控），操作完成后点击按钮一次性提交。

### 3.5 前端自动回调机制

对于自动推模式（方案①/②），前端收到 `terminal_complete` 事件后自动处理：

```javascript
// 前端 Socket/SSE 事件监听
socket.addEventListener('terminal_complete', async (event) => {
    const { msgId } = JSON.parse(event.data);

    // 1. 获取终端输出
    const resp = await fetch(`/api/terminal/output/${msgId}`);
    const { output } = await resp.json();

    // 2. 自动构造消息发送给 AI
    const message = `[终端输出]\n<terminal_output>\n${output}\n</terminal_output>`;

    // 3. 追加到对话上下文并发送
    appendMessage('user', message);
    sendChat(message, /* rebuild history */);
});
```

### 3.6 buffer 存储与清理

```
buffer 存储: _terminal_injections[msgId].buffer → List[bytes]
上限: 10MB (超出时截断，标记 truncated=True)
清理策略:
  - consumed=True → 保留 30 秒后清理（供前端后续访问）
  - completed=True + consumed=True → 立即清理
  - 系统自动清理超过 5 分钟的已结束注入
```

---

## 4. 关键设计决策

### 4.1 为什么硬编码包装命令，而不是改 prompt？

| 方案 | 优劣 |
|------|------|
| **改 prompt** 让 AI 自觉加 echo "DONE" | 不可靠，AI 可能忘记或加错格式 |
| **AI 自觉判断** interactive | 不准确，AI 无法预知命令是否交互 |
| **硬编码包装**（选此方案） | 100% 可靠，代码层确保标记存在 |
| **自动判断** interactive（`_guess_interactive`） | 覆盖 90% 场景，不依赖 AI |

### 4.2 为什么自动推 / 用户推分界？

**核心判断标准：命令是否有明确的"结束"信号**

- 有结束 → 自动推 (git commit, make build, docker pull)
- 没结束但输出稳定 → 自动推 (服务器启动后的 3 秒静默)
- 没结束 + 需要用户操作 → 用户推 (vim, htop, python shell)

### 4.3 为什么用 echo "###AI_END###" 而不是 shell 内置？

```bash
# 方案 A（选此方案）：echo "###AI_END###"
echo "###AI_START###"
npm install
echo "###AI_END###"
# → buffer 中能可靠检测到 "###AI_END###"

# 方案 B（不选）：$? 返回值检查
npm install
ai_exit_code=$?
# → 需要额外逻辑处理，且 PTY 中检测复杂
```

### 4.4 与 Claude Code 的对比

| 维度 | Claude Code | FlyPig v7 |
|------|-------------|-----------|
| 终端呈现 | 无独立终端面板，CLI 界面 | xterm.js 独立终端面板 |
| 执行模型 | 持久 bash session + stdin/stdout pipe | 持久 PTY + WebSocket 字节管道 |
| 输出回传 | 10 秒静默自动回传 | END 标记 + 3 秒静默，自动回传 |
| 交互式支持 | 不支持（文档明确） | 支持（用户操作后手动推送） |
| 用户交互 | 无"按钮"概念 | 交互式命令有按钮入口 |
| 输出截取 | 大输出截断，保留最后5行 | 10MB buffer 上限截断 |
| 后台进程 | 与主会话分离 | persist=True 后台任务管理 |

**结论**：核心逻辑一致——非交互式自动回传，只是端点（AI 分析后自动继续 vs AI 分析后等待用户输入）的实现形式不同。

---

## 5. 与 VS Code Shell Integration 对比

VS Code 的 Shell Integration（OSC 633 协议）是更成熟的方案：

- PTY 输出中嵌入 `\x1b]633;...\x07` 逃逸序列标记
- 标记命令开始、结束、当前目录等
- 前端解析这些标记，实现输出分块、命令导航

**为什么不采用**：
1. 复杂度高，要求 shell 支持 PROMPT_COMMAND / precmd 注入
2. 我们的场景只需 START/END 两个标记，无需按命令分块
3. 用户同时在终端手动操作时，OSC 633 的标记边界可能混乱

---

## 6. 文件改动清单

| 文件 | 改动内容 | 优先级 |
|------|---------|--------|
| `flypig/tools.py` | `_run_terminal_interactive()` 添加 interactive 参数；新增 `_guess_interactive()`；硬编码包装 START/END | P0 |
| `flypig/web/server.py` | `pty_reader` 添加 END 标记检测 + 3 秒静默检测 + `trigger_auto_push()`；新增 `terminal_complete` SSE 事件推送 | P0 |
| `flypig/web/static/index.html` | 前端 SSE 监听 `terminal_complete` 自动 callback；交互式模式下常驻按钮 UI | P0 |
| `flypig/web/terminal.py` | 无改动 | - |
| `flypig/agent.py` | 无改动（INJECTED 透传机制已够用） | - |

### 实现步骤

1. **P0 - tools.py**：添加 `_guess_interactive()` + 修改 `_run_terminal_interactive`
2. **P0 - server.py**：pty_reader 加入完成检测 + `trigger_auto_push`
3. **P0 - 前端**：SSE 监听 `terminal_complete` 事件 + 自动调 `/api/chat`
4. **P1 - 前端**：交互式模式下常驻按钮 UI 改造
5. **P2 - 测试**：三种场景的端到端测试

---

## 7. 完整数据流总览图

```
┌─────────────────────────────────────────────────────────────────┐
│                      非交互式命令 (自动推)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AI → run_cmd("npm install", interactive=False)                 │
│    ↓ tools.py: 包装命令                                         │
│    echo "###AI_START###"                                         │
│    npm install                                                    │
│    echo "###AI_END###"                                           │
│    ↓ 注册 injection → push SSE "terminal_inject"                │
│    ↓ 返回 [TERMINAL_INJECTED:...]                                │
│  AI 继续推理 (不等待)                                            │
│                                                                  │
│  [独立线程/py_reader]                                            │
│  PTY 执行 npm install...                                         │
│  buffer 追加到 inj["buffer"]                                     │
│  检测到 "###AI_END###" → completed=True                          │
│  → push SSE "terminal_complete" → 前端自动调 /api/chat          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   耗时命令/无标记 (静默自动推)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AI → run_cmd("npm run dev", interactive=False)                 │
│    ↓ START/END 包装                                              │
│    echo "###AI_START###"                                         │
│    npm run dev                                                    │
│    echo "###AI_END###"  ← 服务器不退出，永不输出                  │
│    ↓                                                             │
│  pty_reader: 3 秒无新输出 + 无 END 标记                          │
│  → silent_complete=True                                          │
│  → push SSE "terminal_complete" → 自动回调                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        交互式命令 (用户推)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AI → run_cmd("vim", interactive=True)                          │
│    ↓ 不包装，直接注入                                            │
│  pty_reader: 不做完成检测                                        │
│  前端: 显示 🔵 交互模式 + 常驻按钮                              │
│                                                                  │
│  用户在终端操作...                                               │
│  操作完点击 "发送给 AI 分析"                                     │
│  → GET /api/terminal/output → POST /api/chat                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```
