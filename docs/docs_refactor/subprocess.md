# Subprocess 执行策略

> **来源**: `architecture-refactor.md` §3.4.2, §3.4.3
> **关联文档**: `tools.md`（工具定义）、`backend-modules.md`（模块职责）
> 只涉及命令执行策略，工具注册和参数设计见 `tools.md`。

## 核心哲学

AI 调用工具 = AI 的思考过程。工具执行结果（包括报错）原样返回给 AI，不做任何预处理：

```
AI 决定调 tool_bash("ls -la")
  ↓
ToolExecutor 透传到具体实现（subprocess 或 MCP server）
  ↓
执行结果原样返回（成功/报错都不加工）
  ↓
喂回 AI loop
  ↓
AI 自行判断：
  ├── 报错了？→ 读错误信息 → 决定修代码 / 换参数 / 换方案 / 问用户
  ├── 成功但要继续？→ 调下一个工具
  └── 任务完成？→ 给用户输出总结
```

**不需要**：
- 错误计数器
- 错误前缀分类
- 自愈特殊流程
- 重试阈值 / 系统提示词规则

ToolExecutor 就是一条直连线：**收到 tool_call → 执行 → 原始结果返回给 AI**。

> 工具注册、参数设计、@tool 装饰器等见 `tools.md`。

---

## Subprocess 策略

AI 所有命令操作统一使用 subprocess，不再有 PTY 路径。

| 命令类型 | 策略 | 实现 | AI 如何获取结果 |
|---------|------|------|---------------|
| **快速命令**（pip install, git, ls） | 同步等待 | `asyncio.create_subprocess_shell` + `proc.communicate(timeout=30)` | 返回 stdout+stderr 直接给 LLM |
| **后台长任务**（python server.py, npm run dev） | 异步后台 | `subprocess.Popen(stdout=PIPE, stderr=PIPE)` + 返回 PID | AI 通过 `task_log(pid)` 工具获取实时缓存的日志 |
| **交互式脚本**（含 input()） | 先跑再告知 | 先用 subprocess 跑，阻塞前的输出当 tool_result 喂给 AI | AI 判断后告知用户去手动终端 |

### 安全限制（路径访问控制）

所有文件操作默认限制在 workspace 目录内。超出时弹审批让用户决定，不硬拦截：

```python
# tool_bash.py / tool_file.py 执行前
WORKSPACE_ROOT = Path(config.workspace).resolve()
_SENSITIVE_PATHS = ["~/.ssh", "~/.gnupg", "/etc/shadow", "/etc/passwd"]

def _check_path_access(path: str) -> str:
    """返回 'allow' / 'ask' / 'deny'"""
    resolved = Path(path).expanduser().resolve()
    if str(resolved).startswith(str(WORKSPACE_ROOT)):
        return "allow"
    for sensitive in _SENSITIVE_PATHS:
        if str(resolved).startswith(str(Path(sensitive).expanduser().resolve())):
            return "deny"
    return "ask"  # 工作区外但非敏感 → 弹审批
```

| 结果 | 行为 | 例子 |
|------|------|------|
| `allow` | 直接执行 | 工作区内的文件 |
| `ask` | 弹审批卡片，用户确认后执行 | 用户说"帮我改下 `~/.bashrc`" |
| `deny` | 直接拒绝，提示"无权访问" | `~/.ssh/id_rsa`、`/etc/shadow` |

同时配合 Casbin 策略（已在 `backend-modules.md` 定义）：

| 操作 | 策略 | 效果 |
|------|------|------|
| `write_file:.bashrc` | deny | AI 不能修改用户 shell 配置 |
| `terminal:rm -rf /` | deny | 禁止全局删除 |
| `terminal:git push --force` | ask | 弹审批才能执行 |
| 其他未匹配 | allow | 默认允许 |

---

## 后台任务监控（task_log）

```python
_BACKGROUND_PROCESSES: dict[int, dict] = {}  # pid → {process, stdout_buffer, ...}

def start_background(cmd: str) -> int:
    """启动后台进程，返回 PID"""
    proc = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True, text=True, bufsize=1)
    thread = threading.Thread(target=_read_loop, args=(proc, pid), daemon=True)
    thread.start()
    return pid

def task_log(pid: int) -> str:
    """AI 调用此工具获取后台进程的实时日志"""
    info = _BACKGROUND_PROCESSES.get(pid)
    if not info:
        return "[TASK NOT FOUND]"
    return "".join(info["buffer"])
```

**场景示例**：
- 用户"帮我启动服务器" → AI bash("python server.py") → 转为后台 → "服务器已启动(PID: 12345)"
- 用户"帮我获取服务器日志" → AI task_log(12345) → 返回累计的 stdout/stderr

---

## 终端重构核心变化

| 维度 | 旧设计 | 新设计 |
|------|--------|--------|
| 终端归属 | AI 管理的交互式终端 | **用户手动操作的独立终端** |
| AI 能力 | 注入命令到 PTY，管理交互 | **AI 永不操作终端** |
| 命令输出 | PTY 输出 → SSE → 前端卡片 | subprocess 输出直接返回给 AI |
| 交互式命令 | AI 检测 + PTY 注入 + 静默检测 | 交给用户，AI 提示"请手动运行" |
| AI 的 bash 工具 | subprocess + PTY 双路径 | **仅 subprocess（单路径）** |

---

## 实时停止执行

```python
@app.post("/api/agent/stop")
async def stop_agent():
    """终止所有正在运行的后台进程和工具调用"""
    for pid, info in _BACKGROUND_PROCESSES.items():
        try:
            os.kill(pid, signal.SIGTERM)
            await asyncio.sleep(1)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    Container.get("agent").reset()
    return {"ok": True, "killed_pids": list(_BACKGROUND_PROCESSES.keys())}
```

---

## 思考过程实时推流

```python
# chat_node 中
async for chunk in llm.astream(messages):
    if chunk.type == "reasoning":  # 思考过程
        yield {"type": "reasoning", "content": chunk.content}
    elif chunk.type == "text":     # 最终输出文本
        yield {"type": "token", "content": chunk.content}
```

前端收到 `reasoning` 事件时显示在对话气泡上方，用灰字 + 斜体表示"AI 正在思考"。

---

## 终端面板设计

```
底部终端面板 = 单面板，标签页混排
│
├── 用户手动创建（点"+"）：PTY 标签
│   └── xterm.js + WebSocket，有光标可交互
│
├── AI subprocess 触发（点卡片"[在终端查看]"）：只读输出标签
│   └── OutputViewer 组件，只读无光标
│   └── 标签名不带特殊标记，用户看起来和 PTY 标签一样
│
└── TerminalTab.vue 内部根据 isPTY 属性区分：
      isPTY=true  → 嵌入 xterm.js（交互）
      isPTY=false → 嵌入 OutputViewer（只读）
```

---

## 交互式命令策略

```
旧方案：AI 检测到交互式 → 不运行，直接返回提示
新方案：AI 检测到交互式 → 先用 subprocess 跑
  → 把阻塞前的输出收集
  → 输出正常喂给 AI（和 tool_result 一样）
  → AI 看到输出后判断"这是交互式"，回复用户：
    "这个命令需要交互式输入，请在下方终端手动运行"
  → 不再有 _guess_interactive() 等检测代码
```

⚠️ 危险命令可能在半路卡住前就已部分执行。应对：
1. 已知危险命令通过 Casbin 策略预先拦截
2. subprocess 设严格 timeout（默认 30s）
3. 交互式命令永远不自动执行

---

## 环形缓冲区覆盖早期日志

长时间运行的后台进程，缓冲区内存在上限：

解决方案：
- 增加 `task_log_tail(pid, lines=100)` 接口
- 按时间分片写入临时文件 `/tmp/task_logs/{pid}/`
- `task_log` 可按 `since=<timestamp>` 参数获取指定时段日志

---

## 沙箱执行（P1 可选）

### 沙箱生命周期

| 阶段 | 动作 | 生命周期 |
|:----:|------|:--------:|
| **主沙箱** | 会话第一条 subprocess 时 `docker run` | 随会话销毁 |
| **后台沙箱** | AI 启动长服务时新建独立容器 | 服务停止或会话销毁 |
| **降级** | Docker 不可用 → 直接宿主机 subprocess | 当前命令 |

```
AI 调 tool_bash("npm install")
  → SandboxManager.check()
    ├── Docker 可用 → docker exec sandbox_<session> npm install
    │                 → 成功：[🔒 沙箱] npm install ...
    │                 → 失败（容器挂了）→ 重建 → 重试
    └── Docker 不可用 → 宿主机 subprocess
                        → [🔓 本地] npm install ...
```

### 沙箱分配策略

```
主沙箱（一个会话一个，复用）:
  pip install flask
  git status
  grep def login

后台沙箱（每个长服务一个）:
  [🔒 后端] python server.py        ← 容器 1
  [🔒 前端] npm run dev             ← 容器 2

所有沙箱挂载同一 workspace 目录。
后台沙箱数量无上限，会话销毁时全部清理。
```

### 沙箱内自愈（优先于降级）

AI 在沙箱内执行命令失败时，应先在沙箱内安装缺少的工具：

```
AI: npm install
  → 沙箱内报错 "npm: command not found"

❌ 立刻降级：
  → [🔓 本地] npm install

✅ 沙箱内自愈：
  → 检查系统 → apt-get install npm
  → 重新 npm install
  → 实在不行 → [降级到本地] npm install
```

通过 system prompt 约束 AI 行为（`developer.md` 加一句）：
```
"你运行的命令都在沙箱（Docker 容器）里。优先在沙箱内安装依赖，
只有反复安装失败才切换到宿主机执行，切换时注明 [降级到本地]。"
```

### 执行优先级链

```
🥇 AI subprocess 在沙箱内    ← pip install, git status（默认）
🥇 AI 交互式在沙箱内          ← python REPL, vim，提示用户去沙箱终端
🥇 用户交互式在沙箱内          ← 用户手动开终端 → docker exec -it sandbox
🥈 AI subprocess 在沙箱外    ← Docker 不可用时降级
🥉 用户 PTY 在沙箱外          ← Docker 不可用时用户手动终端
```

### 终端实现

```python
# backend/terminal.py
class Terminal:
    async def open(self, session_id: str, sandbox_id: str = None):
        if sandbox_id:
            self.proc = await asyncio.create_subprocess_exec(
                "docker", "exec", "-it", sandbox_id, "bash"
            )
            self.env_label = "🔒 沙箱"
        else:
            self.proc = await asyncio.create_subprocess_exec("bash")
            self.env_label = "🔓 本地"
```

### SSE 事件

```python
# tool_call 结果中携带沙箱状态
{"type": "tool_call",
 "tool": "bash",
 "args": "npm install",
 "sandbox": "active",         # active / fallback / none
 "result": "added 152 packages..."}

# terminal 连接时
{"type": "terminal_open",
 "sandbox": "active",
 "label": "🔒 沙箱终端"}
```

### 沙箱降级配置

| 策略 | 行为 |
|------|------|
| `always` | 强制沙箱，不可用时报错 |
| `prefer` | 优先沙箱，不可用降级本地（默认） |
| `never` | 永远不用沙箱 |

```python
# config.py
SANDBOX_MODE: str = "prefer"
```
