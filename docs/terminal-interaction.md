# FlyPig 终端交互设计

> 设计文档 · 2026-05-17 · v6（Web UI + xterm.js 架构）

> **注意**：FlyPig 已于 2026-05-17 从 Textual TUI 迁移至 Flask + Vue 3 + xterm.js Web UI。
> 终端交互的核心架构（Docker Sandbox + Dual-Path）保持不变，前端渲染层由 Textual Widget 改为 xterm.js。

## 一、概述

### 1.1 设计理念

用户使用终端的真实场景：
- **~90% 时间**：看着 Agent 干活——命令输出在对话区内联显示，无需用户干预
- **~10% 时间**：自己想操作——在终端面板手动敲命令、调试、验证

因此核心设计原则是：
- **Agent 的命令自动执行**，不需要卡住等用户审批
- **输出在对话区内联显示**（折叠式条目，像 CodeBuddy 一样）
- **终端面板是给用户自己用的**（相当于 VS Code 的 "+" 新建终端）
- **审批改为"随时可中止"**——不是"先批准后执行"，而是"自动执行，可点击中止"

### 1.2 Dual-Path 架构（v5 核心变更，v6 沿用）

为了解决 Windows PTY（pywinpty）在编码、控制序列、CLIXML 等方面的持续兼容性问题，v5 引入 **Dual-Path 架构**：

```
                    ┌──────────────────────────────────┐
  Agent 执行命令    │   Docker Sandbox (docker exec)   │ ← 纯 subprocess，无乱码
                    │   `capture_output=True`           │ 返回干净文本
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
  用户手动操作      │   xterm.js 终端面板               │ ← 浏览器真终端，可交互
                    │   WebSocket → PTY bridge          │ 零乱码问题
                    └──────────────────────────────────┘
```

**两条路径互不干扰：**
- Agent 跑命令 → `docker exec` (subprocess)，**完全绕开 PTY 兼容层**，返回纯文本 stdout
- 用户想手动敲命令 → xterm.js 终端面板，WebSocket 桥接到后端 PTY 进程

### 1.3 参考产品

| 产品 | 模式参考 |
|------|---------|
| **VS Code 集成终端** | 真 PTY 终端，多标签，直接交互 |
| **CodeBuddy** | 工具调用输出在对话区动态内联显示 |
| **VS Code Copilot CLI** | AI 自动执行命令，用户可以 review |

---

## 二、整体架构

### 2.1 三栏布局中的终端

```
┌──────────┬──────────────────────────────────────┬────────────────┐
│          │  [plan.md] [hooks.py] [+]             │  💬 对话        │
│  📁 目录  ├──────────────────────────────────────┤  (折叠式)       │
│   树     │  代码内容 (TextArea)                  │                │
│          │                                      │  ┌──────────┐  │
│          ├──────────────────────────────────────┤  │ 🔧 bash   │  │
│          │  [#1 powershell] [#2 npm] [+]         │  │ npm i     │  │
│          │  ┌────────────────────────────────┐  │  │ [输出...]  │  │
│          │  │ PS C:\flypig> npm install       │  │  │ [▶确认]   │  │
│          │  │ + express@4.18.2               │  │  └──────────┘  │
│          │  │ added 50 packages              │  │                │
│          │  │ PS C:\flypig> _                │  │  ┌──────────┐  │
│          │  └────────────────────────────────┘  │  │ 🔧 bash   │  │
│          │                                      │  │ py main   │  │
│          │                                      │  │ ✓ 已完成   │  │
│          │                                      │  └──────────┘  │
├──────────┴──────────────────────────────────────┴────────────────┤
│  [输入框 Input]                                                   │
├──────────────────────────────────────────────────────────────────┤
│  状态栏                                                    ← || →│
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| **Agent 命令执行** | Docker `docker exec` | 纯 subprocess，返回干净文本，无乱码 |
| **用户交互终端** | `xterm.js` + WebSocket | 浏览器端真终端仿真，Flask 后端桥接 |
| **终端仿真** | xterm.js（浏览器） | 成熟稳定，无需 pyte |
| **终端面板** | Vue 3 组件 | 基于 xterm.js Addon，多标签管理 |
| **沙箱管理** | `sandbox.py` | Docker 容器生命周期 + 安全加固 |

### 2.3 数据流（Dual-Path）

```
用户提问 "帮我安装 express"
  │
  ▼
Agent 调用 tool_bash("npm install express")
  │
  ▼ ──── Dual Path 分流 ────
  │
  ├── [Agent 路径] Docker Sandbox ──────────────────────
  │  │
  │  sandbox_manager.run_command("npm install express")
  │  │  → docker exec flypig-sandbox timeout 60 bash -c '...'
  │  │  → subprocess.run(capture_output=True)  ← 纯文本，无乱码
  │  │
  │  ▼ ──── 步骤 2: 输出在对话区显示 ────
  │  │
  │  ┌──────────────────────────────────────┐
  │  │ 🔧 bash                              │
  │  │ $ npm install express                │ ← 命令
  │  │ ─────────────────────────            │
  │  │ added 50 packages in 3.2s            │ ← 输出（折叠式）
  │  └──────────────────────────────────────┘
  │  │
  │  ▼ ──── 步骤 3: 同步到终端标签 ────
  │  │
  │  中栏终端区创建静态标签 [#2 npm install]
  │  输出写入 pyte 屏幕缓冲区（用户可点击查看）
  │  │
  │  ▼ ──── 步骤 4: 结果返回 AI ────
  │  │
  │  Agent 收到 sandbox_manager 返回的文本
  │  继续后续对话
  │
  ├── [用户路径] PTY 终端 ────────────────────────────
  │
  │  用户在终端区域手动输入 "npm test"
  │  → PTY write("npm test\r\n")
  │  → pywinpty 读取输出 → pyte 渲染
  │  → 对话区不产生卡片（纯用户操作）
  │
  └────────────────────────────────────────────────
```

---

## 三、核心模块设计

### 3.1 `PtySession` — 单个 PTY 会话

```python
class PtySession:
    """单个终端会话（一个 shell 进程）"""

    def __init__(self, shell_cmd: str = "powershell.exe"):
        self.shell_cmd = shell_cmd
        self.process = None  # pywinpty.PtyProcess or pty 子进程
        self._output_cb = None
        self._reader_thread = None
        self._alive = False

    def start(self):
        """启动 shell 进程"""
        # Windows: pywinpty.PtyProcess.spawn(self.shell_cmd)
        # Unix:    pid, fd = pty.fork(); if pid==0: exec(shell)

    def write(self, data: str):
        """写入 stdin"""
        # self.process.write(data)

    def resize(self, cols: int, rows: int):
        """调整终端大小"""
        # Windows: process.set_size(cols, rows)
        # Unix:    struct winsize → ioctl(fd, TIOCSWINSZ)

    def stop(self):
        """停止 shell 进程"""
        # process.terminate(); process.close()

    def set_output_cb(self, cb):
        """注册输出回调"""
        self._output_cb = cb

    def is_alive(self) -> bool:
        return self._alive
```

### 3.2 `TerminalScreen` — pyte 屏幕缓冲区

```python
from pyte import Screen, Stream

class TerminalScreen:
    """终端屏幕缓冲区（pyte 封装）"""

    def __init__(self, cols: int = 80, rows: int = 24):
        self.screen = Screen(cols, rows)
        self.stream = Stream()
        self.stream.attach(self.screen)
        self._history = []  # 滚动历史

    def feed(self, data: str):
        """接收原始 ANSI 数据"""
        self.stream.feed(data)

    def get_display_lines(self) -> list[str]:
        """获取当前显示的所有行"""
        return self.screen.display

    def get_plain_text(self) -> str:
        """获取纯文本（供 LLM 读取）"""
        return "\n".join(self.screen.display).strip()

    def get_cursor_position(self) -> tuple:
        """获取光标位置 (x, y)"""
        return (self.screen.cursor.x, self.screen.cursor.y)

    def resize(self, cols: int, rows: int):
        self.screen.resize(rows, cols)

    def reset(self):
        self.screen.reset()
```

### 3.3 `TerminalCard` — 卡片数据模型

```python
@dataclass
class TerminalCard:
    """对话区终端卡片数据"""
    card_id: str
    command: str
    status: str = "pending"  # pending | streaming | completed | rejected | running
    output_buffer: str = ""
    tab_id: Optional[int] = None   # 批准后关联的终端标签 ID
    tab_idx: int = -1
    created_at: float = 0.0
    completed_at: Optional[float] = None
```

### 3.4 `TerminalPanel` — Vue 3 + xterm.js 终端面板

```vue
<template>
  <div class="terminal-panel">
    <div class="terminal-tabs">
      <span v-for="tab in tabs" :key="tab.id"
            :class="{active: tab.id === activeTab}"
            @click="switchTab(tab.id)">{{ tab.name }}</span>
      <button @click="createTab">+</button>
    </div>
    <div ref="terminalContainer" class="terminal-container"></div>
  </div>
</template>
```

后端 WebSocket 桥接：

```
浏览器 (xterm.js)                   服务器 (Flask + WebSocket)
  │                                        │
  │  WebSocket 连接                         │
  │────────────────────────────────────────>│
  │                                        │
  │  用户敲键 → xterm 输出 ANSI 序列        │
  │  ───────── via WebSocket ───────────>│  → PTY stdin write()
  │                                        │
  │  PTY stdout 数据                      │
  │  <───────── via WebSocket ──────────│  ← PTY reader thread
  │                                        │
  │  xterm.write(data) → 终端渲染          │
```

---

## 四、交互流程详解

### 4.1 Agent 执行命令（Docker Sandbox 路径）

```
对话区                 终端区                    Agent
────────────────────────────────────────────────────────────
[Agent] 我需要检查       (当前标签 #1)          [思考] 需要运行命令
当前项目依赖              PS C:\flypig> _
                         [用户正在打字...]

[🔧 bash]                                     → tool_bash(
  $ docker exec flypig-sandbox                   command="npm install
  timeout 60 bash -c 'cd /workspace               express",
  && npm install express'                         timeout=60
  [输出直接返回，无需用户确认]                   )
  │
  ▼ ──── 输出返回到对话区 ────
  │
  + express@4.18.2
  added 50 packages in 3.2s
  │
  ▼ ──── 同步到终端标签 ────
  │
  [#2 npm install]  (静态标签，显示 docker 输出)
  │
  ▼
  [Agent] 已安装 express，
  当前版本 4.18.2
```

### 4.2 用户在终端直接输入（PTY 路径）

```
用户点击终端区域 → 获取焦点 → 输入 "npm test"
→ PTY 写入 "npm test\r\n"
→ 终端正常显示命令执行
→ 对话区不产生卡片（用户自主操作）
→ 用户可通过 /sync 命令让 AI 查看当前终端输出
```

### 4.3 多标签管理（用户 PTY 标签）

```
用户点击 [+]
  │
  ▼
弹出默认 shell 选项（或直接创建新终端标签）
  │
  ▼
新标签 [#3 cmd] 创建
  │
  ▼
独立的 PTY 进程 + 独立的 pyte Screen
  │
  ▼
用户可以在 #2 运行 dev server，在 #3 运行测试
互不干扰
```

### 4.4 交互式命令（python -i, node REPL）

交互式命令只通过用户手动 PTY 操作。Agent 不直接写入 PTY。

```
用户在中栏终端 #2 手动输入 "python -i"
  │
  ▼
python -i 启动 → 显示 >>> 提示符
  │
  ├─ 用户手动输入 "import math"
  ├─ 用户手动输入 "math.sqrt(16)"
  ├─ 输出 "4.0"
  └─ 用户手动输入 "exit()"
```

### 4.5 Agent 命令结果查看

Agent 通过 `docker exec` 执行的命令，其输出显示在两个地方：

1. **对话区**（折叠式卡片，展开可见全部输出）
2. **中栏终端标签**（静态标签，无 PTY，纯显示输出）

```
Agent 执行 docker exec "npm install express"
  │
  ├── 对话区: 🔧 bash + 折叠式输出
  │
  └── 中栏: 新建标签 [#2 npm install]
             点击标签显示输出（pyte 缓冲区）
```

> 静态标签与 PTY 标签的区别：
> - 静态标签：无后台 shell，纯显示文本，适合查看命令结果
> - PTY 标签：有后台 shell 进程，可交互打字，适合用户主动操作

---

## 五、TerminalCard（对话区卡片）设计

### 5.1 卡片状态机

```
                  ┌──────────┐
                  │  pending  │ ← 刚创建，等待输出
                  └────┬─────┘
                       │
                  ┌────▼─────┐
                  │ streaming │ ← 正在接收实时输出
                  └────┬─────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
    ┌─────▼────┐ ┌─────▼────┐ ┌────▼─────┐
    │completed │ │ rejected  │ │ running   │
    │ (✓ 完成) │ │ (✕ 拒绝)  │ │ (终端执   │
    └──────────┘ └──────────┘ │ 行中)     │
                              └──────────┘
```

### 5.2 卡片样式

```
状态: pending
┌──────────────────────────────────┐
│ 🔧 bash                          │
│ $ npm install express             │
│ ───────────────────────           │
│ [模拟输出...]                      │
│ ───────────────────────           │
│ [▶ 确认]  [✕ 拒绝]               │
└──────────────────────────────────┘

状态: streaming (预览中)
┌──────────────────────────────────┐
│ 🔧 bash                          │
│ $ npm install express             │
│ ───────────────────────           │
│ npm http fetch GET 200 ...       │
│ + express@4.18.2                 │
│ ───────────────────────           │
│ [▶ 确认并在终端运行]  [✕ 拒绝]    │
└──────────────────────────────────┘

状态: completed (已执行)
┌──────────────────────────────────┐
│ ✓ bash                           │
│ $ npm install express             │
│ ───────────────────────           │
│ + express@4.18.2                 │
│ added 50 packages                │
│ ───────────────────────           │
│ 点击终端标签 #2 查看完整输出       │
└──────────────────────────────────┘

状态: rejected
┌──────────────────────────────────┐
│ ✕ bash                           │
│ $ npm install express             │
│ ───────────────────────           │
│ [用户拒绝执行]                    │
└──────────────────────────────────┘

状态: running (已在终端运行中)
┌──────────────────────────────────┐
│ ▶ bash                           │
│ $ npm install express             │
│ ───────────────────────           │
│ 终端标签 #2 执行中...             │
│ [跳转到 [#2]]                     │
└──────────────────────────────────┘
```

---

## 六、命令完成检测

### 6.1 Agent 命令（Docker Sandbox）

Agent 命令通过 `sandbox_manager.run_command()` 阻塞执行，**天然同步**——`docker exec` 命令结束即返回，无需检测提示符：

```python
def run_command(self, command, timeout=120):
    result = subprocess.run(
        ["docker", "exec", self._container_name,
         "timeout", str(timeout), "bash", "-c",
         f"cd /workspace && {command}"
        ],
        capture_output=True, text=True,
        timeout=timeout + 10,
    )
    return (result.stdout + result.stderr).strip()
```

### 6.2 用户 PTY 命令

PTY 中的用户输入不需要"完成检测"——用户自己在终端里操作，Agent 不干预。

`/sync` 命令可将当前 PTY 终端的屏幕内容同步到对话区供 AI 参考。

---

## 七、文件清单与实现计划

### 7.1 关键文件

| 文件 | 说明 |
|------|------|
| `flypig/tools.py` | `_run_inline`: Web 模式走 `sandbox_manager.run_command()` |
| `flypig/sandbox.py` | Docker 沙箱管理器，`run_command()` 提供 `docker exec` 阻塞执行 |
| `flypig/web/server.py` | Flask 后端，SSE 事件推流 + WebSocket 终端桥接 |
| `flypig/web/static/index.html` | Vue 3 SPA，xterm.js 终端面板 |
| `docs/terminal-interaction.md` | 本文档（v6） |

### 7.2 实施顺序

| Phase | 内容 | 文件 |
|-------|------|------|
| **1** | Flask + Vue 3 三栏布局 | `web/server.py`, `web/static/index.html` |
| **2** | xterm.js 终端面板 + WebSocket PTY 桥接 | `web/server.py`, `web/static/index.html` |
| **3** | 交互式命令支持 | `tools.py`, `sandbox.py` |
| **4** | 标签管理（多终端标签页） | `web/static/index.html` |
| **5** | 测试验证 | 所有 |

---

## 八、Web UI 终端架构

### 8.1 `_run_inline` 的改动

当前 `tools.py:ToolExecutor._run_inline()` 使用 `subprocess.run()` 执行命令。Web 模式下始终走 inline 执行：

```python
def _run_inline(self, command, timeout_val, persist):
    if self.sandbox_manager:
        return self.sandbox_manager.run_command(command, timeout_val, "/workspace")
    # fallback: 本地 subprocess（无 Docker 时）
    return self._run_local_subprocess(command, timeout_val, persist)
```

### 8.2 终端面板（xterm.js）

- 浏览器端 xterm.js 渲染真终端
- 后端 Flask + WebSocket 桥接 PTY 进程
- 输出通过 SSE 同时推送到对话区

### 8.3 沙箱模式

使用 `create_sandbox_components()` 自动检测 Docker 可用性。不可用时自动降级为本地 subprocess。

---

## 九、开放问题

1. ~~**Windows PTY 兼容性**~~：✅ 已通过 Dual-Path 架构解决。Agent 命令走 `docker exec`，完全绕开 PTY
2. **大规模输出**：长时间命令可能产生大量输出，需要输出截断策略
3. **Docker 不可用降级**：无 Docker Desktop 时降级为本地 subprocess
4. **WebSocket 重连**：浏览器断线后 xterm.js 需恢复会话
