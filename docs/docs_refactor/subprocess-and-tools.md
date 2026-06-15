# Subprocess 策略与工具

> **来源**: `architecture-refactor.md` §3.4.2, §3.4.3, §3.7.2
> **关联文档**: `backend-modules.md`（工具列表）、`adversarial-system.md`（lint/change_review 工具）
> 改工具实现时，需同步检查 backend-modules.md 中的工具列表。

## 核心哲学：工具调用是 AI 的反射外延

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
- 错误计数器（AI 自己知道失败和上次的区别）
- 错误前缀分类（AI 能读懂 `UnboundLocalError`）
- 自愈特殊流程（AI 有 read/edit 工具，自己会修）
- 重试阈值 / 系统提示词规则（全是硬编码中间层，破坏反射的自然性）

ToolExecutor 就是一条直连线：**收到 tool_call → 执行 → 原始结果返回给 AI**，不做任何加工或状态管理。

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

> **原则**：用户明确要求的操作走 `ask`，让用户自己决定是否信任 AI。系统只拦截明确的高危敏感路径。

同时配合 Casbin 策略（已在 `backend-modules.md` 定义）：

| 操作 | 策略 | 效果 |
|------|------|------|
| `write_file:.bashrc` | deny | AI 不能修改用户 shell 配置 |
| `terminal:rm -rf /` | deny | 禁止全局删除 |
| `terminal:git push --force` | ask | 弹审批才能执行 |
| 其他未匹配 | allow | 默认允许 |

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

## 终端重构核心变化

| 维度 | 旧设计 | 新设计 |
|------|--------|--------|
| 终端归属 | AI 管理的交互式终端 | **用户手动操作的独立终端** |
| AI 能力 | 注入命令到 PTY，管理交互 | **AI 永不操作终端** |
| 命令输出 | PTY 输出 → SSE → 前端卡片 | subprocess 输出直接返回给 AI |
| 交互式命令 | AI 检测 + PTY 注入 + 静默检测 | 交给用户，AI 提示"请手动运行" |
| AI 的 bash 工具 | subprocess + PTY 双路径 | **仅 subprocess（单路径）** |

## 实时停止执行

`/api/agent/stop` 除了标记状态，还需要终止正在运行的 subprocess：

```python
@app.post("/api/agent/stop")
async def stop_agent():
    """终止所有正在运行的后台进程和工具调用"""
    for pid, info in _BACKGROUND_PROCESSES.items():
        try:
            os.kill(pid, signal.SIGTERM)
            await asyncio.sleep(1)
            os.kill(pid, signal.SIGKILL)  # 强制终止
        except ProcessLookupError:
            pass
    # 重置 Agent 状态
    Container.get("agent").reset()
    return {"ok": True, "killed_pids": list(_BACKGROUND_PROCESSES.keys())}
```

## 思考过程实时推流

LLM 推理时前端需要看到推理状态，否则长时间无响应用户以为卡死。在 `chat_node` 中通过 SSE 推送推理过程：

```python
# chat_node 中
async for chunk in llm.astream(messages):
    if chunk.type == "reasoning":  # 思考过程
        yield {"type": "reasoning", "content": chunk.content}
    elif chunk.type == "text":     # 最终输出文本
        yield {"type": "token", "content": chunk.content}
```

前端收到 `reasoning` 事件时显示在对话气泡上方，用灰字 + 斜体表示"AI 正在思考"。

## 终端面板设计

终端面板保持单面板，标签页混排，用户无感：

```
底部终端面板 = 单面板，标签页混排
│
├── 用户手动创建（点"+"）：PTY 标签
│   └── xterm.js + WebSocket，有光标可交互
│
├── AI subprocess 触发（点卡片"[在终端查看]"）：只读输出标签
│   └── OutputViewer 组件，只读无光标
│   └── 标签名不带特殊标记，用户看起来和 PTY 标签一样
│   └── 用户完全无感，只知道"又多了一个终端标签"
│
└── TerminalTab.vue 内部根据 isPTY 属性区分：
      isPTY=true  → 嵌入 xterm.js（交互）
      isPTY=false → 嵌入 OutputViewer（只读，无光标无交互）
      同一个标签组件，同一个渲染容器，用户看不出来区别
```

## 交互式命令策略

```
旧方案：AI 检测到交互式 → 不运行，直接返回提示
新方案：AI 检测到交互式 → 先用 subprocess 跑
  → 把阻塞前的输出（如 python 版本号、脚本的 usage 提示）收集
  → 输出正常喂给 AI（和 tool_result 一样）
  → AI 看到输出后判断"这是交互式"，回复用户：
    "这个命令需要交互式输入，请在下方终端手动运行"
  → 不再有 _guess_interactive() 等检测代码
  → 交互式命令也走同样的 subprocess 路径，只是输出到卡住了而已
```

⚠️ **"先跑再告知"副作用**：危险命令（如 `git push --force`、`rm -rf`）可能在半路卡住前就已经造成部分执行。应对措施：
1. 已知危险命令通过 Casbin 策略预先拦截（如 `deny` 或 `ask` 审批）
2. subprocess 设严格 timeout（默认 30s，可配置），超时自动 kill
3. 交互式命令永远不自动执行——subprocess 阻塞前的输出仅用于 AI 判断"这是交互式"

## 环形缓冲区覆盖早期日志

长时间运行的后台进程（如持续运行的 Web 服务器），缓冲区内存在上限，早期输出可能被后续日志覆盖。

解决方案：
- 增加 `task_log_tail(pid, lines=100)` 接口按需获取末尾 N 行
- 同时按时间分片写入临时文件 `/tmp/task_logs/{pid}/`
- `task_log` 可按 `since=<timestamp>` 参数获取指定时段日志

## 文件编辑方案

⚠️ **关键问题**：简单的 `old_str → new_str` 替换在复杂编辑场景下极易出错——多文件并发修改、缩进破坏、模糊匹配失效、长上下文替换错位。

方案：不重新实现——使用市面上最成熟的方案。

### 方案一（推荐）：Aider 编辑引擎（pip install 即可用）

```python
# infrastructure/tools/tool_file.py
from aider.coders import Coder           # pip install aider-chat
from aider.io import InputOutput

class ToolFile:
    def __init__(self, workspace: str):
        self.io = InputOutput(yes=True)
        self.coder = Coder.create(
            ...  # 配置 edit_format="search-replace"
        )

    def edit_file(self, path: str, old_str: str, new_str: str) -> str:
        return self.coder.commands.cmd_edit(path, old_str, new_str)
        # Aider 自动处理: AST 对齐 / 多匹配选择 / 缩进校正 / 多层回退 / git checkpoint
```

| 能力 | Aider 实现 |
|------|-----------|
| **diff 格式** | 强制 search/replace 统一格式 |
| **AST 对齐** | 解析 AST 找到最接近的匹配块 |
| **多匹配处理** | 选择最佳匹配，忽略白空差异 |
| **回退策略** | 模糊→忽略空白→截断→局部重试 |
| **确定性回滚** | 应用前自动 git checkpoint |

### 方案二（轻量替代）：unified diff + git apply

```python
# infrastructure/tools/tool_file.py（轻量版）
import subprocess, tempfile

def apply_patch(file_path: str, unified_diff: str) -> str:
    """基于 git apply 的标准补丁应用"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as f:
        f.write(unified_diff)
        diff_path = f.name
    result = subprocess.run(
        ["git", "apply", "--reject", "--whitespace=fix", diff_path],
        capture_output=True, text=True
    )
    # git apply 失败时自动尝试 3-way merge
    if result.returncode != 0:
        result = subprocess.run(
            ["git", "apply", "--3way", diff_path],  # 3-way merge
            capture_output=True, text=True
        )
    return result.stdout or result.stderr
```

### 方案三：基于代码图谱的结构化编辑（Graphify + tree-sitter）

**原理**：不依赖文本匹配——Graphify 将代码解析为 AST 知识图谱，AI 通过实体名精确指定编辑位置，系统直接在 AST 节点上做结构化替换。

### 三种方案对比

| 维度 | 方案一（Aider） | 方案二（git apply） | 方案三（Graphify + tree-sitter） |
|------|---------------|-------------------|-------------------------------|
| 原理 | 文本 search/replace + 模糊匹配 | unified diff + fuzz + 3-way | **AST 节点级结构化替换** |
| 准确性 | 较高（有 AST fallback） | 一般（纯文本） | **极高** |
| 速度 | 较慢（加载 Aider 框架） | **极快** | 中等 |
| 复杂度 | 中等 | **最低（2 行代码）** | 高 |
| 依赖 | `aider-chat` | 零 | `tree-sitter` + Graphify |
| 建议 | 生产环境 | **MVP 首选** | **长期目标** |

### 三种方案的集成路线

```
MVP（第 1 轮）:              方案二（git apply）
  ↓ 编辑可靠性够了，但代码理解不足
第 2 轮:                   方案二 + Graphify（只读，用于代码搜索/理解）
  ↓ AI 能理解代码结构了，但编辑仍是文本级
第 3 轮（长期目标）:         方案三（Graphify + tree-sitter 结构化编辑）
                             方案一（Aider）作为结构化编辑失败的 fallback
```

> 三者不冲突，可以共存：tool_file.py 内部可以有三层 fallback——先尝试结构化 AST 替换（方案三），失败则降级到 Aider 模糊匹配（方案一），再失败则降级到 git apply（方案二）。

### 策略模式重构建议

三种文件编辑方案建议用策略模式 + 统一结果类型，提高可读性和扩展性：

```python
@dataclass
class EditResult:
    success: bool
    content: str
    method_used: str     # "git_apply" / "aider" / "ast"
    fallback_chain: list[str]

class FileEditStrategy(ABC):
    @abstractmethod
    async def apply(self, path: str, old: str, new: str) -> EditResult: ...

class GitApplyStrategy(FileEditStrategy): ...
class AiderStrategy(FileEditStrategy): ...
class ASTStrategy(FileEditStrategy): ...

class FileEditor:
    strategies: list[FileEditStrategy] = [ASTStrategy(), AiderStrategy(), GitApplyStrategy()]

    async def edit(self, path, old, new) -> EditResult:
        for strategy in self.strategies:
            result = await strategy.apply(path, old, new)
            if result.success:
                return result
        return EditResult(success=False, ...)
```

**技术栈**：

| 模块 | 采用方案 | 类型 |
|------|---------|------|
| 文件编辑引擎 | **Aider (coder 模块)** 或 **git apply** | 市面方案（开源） |
| git 操作 | **Aider 内部 git 管理** 或 **标准 git** | 市面方案（复用） |
| diff 格式 | **search/replace** 或 **unified diff** | 标准（RFC） |

## `@tool` 自动注册（元编程）

当前设计需手动注册每个工具到 ToolExecutor。建议加装饰器实现声明即注册：

```python
# infrastructure/tools/registry.py
_TOOL_REGISTRY: dict[str, type] = {}

def tool(name=None, category="system", timeout=30):
    def decorator(cls):
        tool_name = name or cls.__name__.removeprefix("Tool").lower()
        _TOOL_REGISTRY[tool_name] = cls
        cls._meta = {"name": tool_name, "category": category, "timeout": timeout}
        return cls
    return decorator

# 使用示例——加工具只需写文件+加 @tool()
@tool(name="bash", category="system", timeout=30)
class ToolBash:
    async def __call__(self, cmd: str, cwd: str | None = None) -> str: ...

# ToolExecutor 自动从注册表加载
class ToolExecutor:
    def get_available_tools(self):
        return {name: cls() for name, cls in _TOOL_REGISTRY.items()}
```

**扩展步骤（加一个新后端工具）**：

```
1. 在 infrastructure/tools/ 对应分组目录下新建 tool_xxx.py
2. 用 @tool 装饰器注册:
     @tool(name="my_tool", description="...")
     def my_tool(args): ...
3. 不需要改前端 — 自动注册到 ToolNode，AI 自行决定是否调用
```

## 工具文件列表（按功能分组）

> 完整工具文件树见 `folder-tree.md` → `flypig/infrastructure/tools/`。
> 以下只列工具名称和职责，不重复文件结构。

| 分组 | 工具 | 职责 |
|------|------|------|
| **file** | tool_read | ★ 读文件（支持 start/end 范围，避免全量 token） |
| | tool_write | 写文件（全量重写，新建/大改时用） |
| | tool_patch_file | ★ 局部更新：按 anchor 定位修改，省 90%+ token |
| | tool_delete | ★ 删除文件 |
| **review** | tool_change_review | 变更审查数据生成 |
| | tool_lint | 代码规范检查（Ruff） |
| | tool_change_score | 变更影响评分 |
| **search** | tool_search | grep + find_files |
| | tool_search_tools | ★ 按 query 搜索可用工具，返回 name+description+schema（懒加载协议用） |
| | tool_call_direct | ★ 按工具名直接调用，name 来自 tool_search_tools 结果 |
| | tool_web_search | ☆ P1 内置网络搜索（DuckDuckGo） |
| **interact** | tool_ask_choice | Explore 选择题 |
| **system** | tool_bash | subprocess 命令 |
| | tool_git | ★ Git 操作：status/diff/log/commit/branch |
| | tool_fetch_url | ★ 网页抓取（httpx + trafilatura） |
| | tool_list_dir | ★ 目录浏览（deep=False 一层，deep=True 递归扫描+统计） |
| | tool_datetime | ★ 取当前时间/时区/日期计算 |
| | tool_calc | ★ 安全数学计算 |
| | tool_task | task_status + task_list + task_log |
| | tool_task_manager | 任务看板 add_task / update_task |
| | tool_ocr | ☆ P1 OCR 文字识别 |
| | tool_extract_archive | 压缩解压（防 Zip Slip） |
| **mcp** | tool_mcp_loader | MCP 服务器加载器 |
| | tool_mcp_manager | MCP 自助安装 |

### 新增基础工具说明

| 工具 | 为什么必备（不靠 bash/MCP） | 核心技术 |
|------|---------------------------|---------|
| `tool_git` | AI 每天几十次 git 操作，裸 bash git 结果混乱、idempotency 难保证 | `subprocess` 封装 git，结构化返回 status/diff/log |
| `tool_fetch_url` | 查文档、看 API 规格，MCP fetch 需要 npx+node，单机不应依赖 | `httpx`（Python 内置兼容） |
| `tool_project_scan` | 每次新会话第一件事就是"看看这个项目是什么"，目前靠 bash ls | `Path.rglob` + `Counter` 统计语言 |
| `tool_datetime` | AI 经常需要知道当前时间、时区、计算日期差 | `datetime` 标准库 |
| `tool_calc` | 让 AI 算 token 数、文件大小、日期差，它经常算错或走危险的 bash eval | `ast.literal_eval` + `Decimal` |

### 新增工具实现方案分析

下表说明每个工具是自写还是用现成库，以及代码量和依赖：

| 工具 | 方案 | 代码量 | 依赖 |
|------|------|--------|------|
| `tool_datetime` | **自写** — `datetime.now()` + `pytz` 搞定 | ~5 行 | 标准库 |
| `tool_calc` | **自写** — `ast.literal_eval` 安全求值，可选 `numexpr` 支持复杂表达式 | ~15 行 | 可选 `numexpr` |
| `tool_project_scan` | **自写** — `Path.rglob("*")` + `Counter` 统计文件后缀分布 | ~20 行 | 标准库 |
| `tool_git` | **`GitPython` 薄封装** — 不自己解析 git 裸输出，用成熟库做二次封装 | ~60 行 | `pip install GitPython` |
| `tool_fetch_url` | **`httpx` + `trafilatura`** — httpx 发请求，trafilatura 把 HTML 转纯文本（去噪比 BeautifulSoup 好） | ~30 行 | `pip install httpx trafilatura` |

**原则**：纯数据操作（时间/计算/扫描）自写，与外部系统交互（Git/HTTP）用成熟库封装。

## 工具参数优化：避免全量读写

核心原则：**工具的参数设计应让 AI 能精确指定操作范围，避免全量传输 token 浪费。**

| 工具 | 优化参数 | 对应场景 |
|------|---------|---------|
| `tool_read` | `start`/`end` → 按行范围读 | 搜到 def login 在 42-58 行 → 只读这一段 |
| `tool_write` | 本身全量写，无优化空间 | — |
| `tool_patch_file` | 已有 `anchor` → 按附近文本定位修改 | 不改完整文件 |
| `tool_search` | `pattern` + `glob` → 精确匹配 | 只搜 "def login" 不读全文件 |
| `tool_git` | `command` → git status/diff/log/commit 等 | 只取指定命令，不跑全量 |
| `tool_bash` | `max_output` → 输出截断 | 限制返回行数 |
| `tool_task_log` | `tail` → 只取尾 N 行 | 不拿全量 10000 行缓冲区 |
| `tool_project_scan` | 自身上下文感知 → 精确扫描 | 只扫指定目录 |

### tool_read 和 tool_patch_file 详细设计

```python
@tool(name="read_file")
def read_file(path: str, start: int = None, end: int = None) -> dict:
    """读取文件内容。支持按行范围读取，避免全量 token 消耗。

    Args:
        path:  文件路径（必填）
        start: 起始行号（可选，从 1 开始）
        end:   结束行号（可选，含该行）

    Returns:
        content: 文件内容
        lines:   文件总行数
        range:   实际返回的行范围
    """
    with open(path) as f:
        lines = f.readlines()

    if start is not None and end is not None:
        content = "".join(lines[start-1:end])
    elif start is not None:
        content = "".join(lines[start-1:])
    else:
        content = "".join(lines)

    return {
        "content": content,
        "lines": len(lines),
        "range": f"{start or 1}-{end or len(lines)}",
    }

@tool(name="patch_file")
def patch_file(path: str, operations: list[dict]) -> dict:
    """对文件做局部更新，不需要输出完整文件内容。
    比全量 write_file 省 90%+ token。

    Args:
        path: 文件路径
        operations: 从后往前执行的操作列表:
          {"op": "insert", "line":10,        "content":"new_line"}
          {"op": "replace","start":20,"end":25,"content":"new_lines"}
          {"op": "delete", "start":30,"end":35}

    与 edit_file 的区别:
      edit_file = 用 old_str/new_str 做文本匹配（Aider/git apply）
      patch_file = 用行号精确定位（不依赖原文是否一致）
    """
    with open(path) as f:
        lines = f.readlines()

    # 从后往前执行，防止行号偏移
    ops = sorted(operations, key=lambda o: o.get("start", o.get("line", 0)), reverse=True)
    for op in ops:
        if op["op"] == "insert":
            lines.insert(op["line"] - 1, op["content"] + "\n")
        elif op["op"] == "replace":
            lines[op["start"]-1:op["end"]] = [op["content"] + "\n"]
        elif op["op"] == "delete":
            lines[op["start"]-1:op["end"]] = []

    with open(path, "w") as f:
        f.writelines(lines)
    return {"success": True, "path": path, "ops": len(operations)}
```

## 工具与知识图谱/AST 的集成

当前工具是 AI 操作的**底层接口**，知识图谱和 AST 是上层**索引层**，不会替代工具，而是让 AI 少调工具：

### 当前（MVP）

```
AI 想理解项目结构:
  1. tool_list_dir(".", deep=True) → 拿到文件树
  2. tool_search("class.*Service") → 搜服务类
  3. read_file("auth_service.py", start=1, end=50) → 读头部结构
  → 3 次工具调用才能摸清一个类的关系
```

### P1 加上知识图谱

```
AI 想理解项目结构:
  1. kg_query("list_classes") → {"ChatService": {"file":"chat.py","methods":["process","validate"]}}
  → 1 次查询，精确返回，不需要逐文件搜索阅读
```

### 工具的分层关系

```
┌─ 用户/对话 ──────────────────────────┐
│                                        │
│  ┌── AI ───────────────────────────┐   │
│  │                                  │   │
│  │  P1+ 优先调用:                   │   │
│  │  ├── kg_query("什么是 ChatService")│   │  ← 知识图谱查询
│  │  ├── kg_query("谁调用了这个")     │   │
│  │  └── vs_query("类似登录的功能")   │   │  ← 向量检索
│  │                                  │   │
│  │  以上查不到时降级调用:             │   │
│  │  ├── search("ChatService")       │   │  ← 文本搜索
│  │  ├── read_file("chat.py")        │   │  ← 读文件
│  │  └── bash("grep -r ChatService") │   │  ← 原始命令
│  │                                  │   │
│  └──────────────────────────────────┘   │
│                                          │
└──────────────────────────────────────────┘
```

知识图谱和 AST **不改变工具的实现**，只改变 AI 的调用策略——先从索引查，查不到再降级到工具。工具本身不变，只是 AI 少调了它们。

subprocess 超时后无法判断远程命令是否已执行，可能导致重复操作：

```
AI 调 bash("git commit -m 'fix'") → 超时 30s → AI 收到 TimeoutError
→ AI 重试 → bash("git commit -m 'fix'") → 第二次成功 → 但第一次也成功了
→ 两个重复的 commit
```

**原则**：耗时工具尽量设计为幂等：

| 操作 | 是否幂等 | 说明 |
|------|---------|------|
| `git commit` | ❌ 不幂等 | 先检查 `git status` 是否有未提交变更 |
| `write_file` | ✅ 幂等 | 写同样的内容 = 没变化 |
| `npm install` | ✅ 幂等 | 重复安装不影响结果 |
| `mkdir -p` | ✅ 幂等 | -p 参数保证 |
| `git push` | ❌ 不幂等 | 添加 `--force-with-lease` 并在出错时告知用户 |

## 命令模式：工具调用可撤销

当前工具调用是"发射后不管"的——AI 执行 `write_file` 或 `bash` 后，若用户驳回变更，需要手动 git 回滚。命令模式将每个工具调用封装为 Command，让撤销成为一等公民：

```python
from abc import ABC, abstractmethod

class ToolCommand(ABC):
    """可撤销的命令"""
    @abstractmethod
    async def execute(self) -> ToolResult: ...
    @abstractmethod
    async def undo(self) -> None: ...

class WriteFileCommand(ToolCommand):
    def __init__(self, path: str, content: str):
        self.path = path
        self.new_content = content
        self.backup: str | None = None

    async def execute(self):
        self.backup = await read_file_content(self.path)  # 先备份
        await write_file(self.path, self.new_content)

    async def undo(self):
        if self.backup is not None:
            await write_file(self.path, self.backup)

class BashCommand(ToolCommand):
    def __init__(self, cmd: str):
        self.cmd = cmd
        self.undo_cmd: str | None = None  # 逆向操作

    async def execute(self):
        result = await bash(self.cmd)
        # 自动推导逆向命令（git add → git reset, mkdir → rm -r）
        self.undo_cmd = self._infer_undo(self.cmd)
        return result

    async def undo(self):
        if self.undo_cmd:
            await bash(self.undo_cmd)

    def _infer_undo(self, cmd: str) -> str | None:
        """简单逆向推导，复杂操作交给 GitCheckpointManager"""
        if cmd.startswith("git add"):
            return cmd.replace("git add", "git reset")
        if cmd.startswith("mkdir"):
            return cmd.replace("mkdir", "rm -rf")
        return None  # 无法推导 → 通知用户手动回滚

class CommandHistory:
    """执行历史栈，支持撤销到任意点"""
    def __init__(self, max_undo=50):
        self._history: list[ToolCommand] = []
        self._max_undo = max_undo
        self._position = -1

    async def execute(self, cmd: ToolCommand):
        await cmd.execute()
        self._history = self._history[:self._position + 1]  # 清除重做栈
        self._history.append(cmd)
        self._position += 1
        if len(self._history) > self._max_undo:
            self._history.pop(0)

    async def undo_last(self):
        if self._position >= 0:
            await self._history[self._position].undo()
            self._position -= 1

    async def undo_to(self, target_index: int):
        """撤销到任意历史点"""
        while self._position >= target_index:
            await self._history[self._position].undo()
            self._position -= 1
```

**与现有系统的关系**：
- `CommandHistory` 的 `undo_to()` 天然对应 CheckpointStore 的 `turn_id → commit_hash` 映射
- 用户驳回变更时 → 系统自动对关联工具调用执行 `undo()` → 再用 git 整体确认
- 命令模式**不取代** git 回滚（严谨场景仍需 git），而是提供**更细粒度的即时撤销**

> **关联文档**: `backend-modules.md`（CheckpointStore）、`adversarial-system.md`（驳回处理）

## Token 优化

### 1. 工具输出源头截断

Pipeline 层压缩是后端防线，但最好在源头就限制工具输出的最大长度。

```python
# tool_bash.py — subprocess 输出截断
@tool(name="bash")
def tool_bash(command: str, max_output: int = 5000):
    result = subprocess.run(command, capture_output=True, timeout=30)
    output = result.stdout[:max_output]
    if len(result.stdout) > max_output:
        output += b"\n...(truncated)..."
    return {"stdout": output.decode(), "stderr": result.stderr.decode()}

# mcp_executor.py — MCP 结果大小限制
MAX_MCP_CHARS = 10_000
async def call_mcp_tool(server, tool, args):
    result = await mcp_client.call_tool(server, tool, args)
    content = result.content[:MAX_MCP_CHARS]
    return {"content": content}

# task_log 默认只返回末尾 200 行（替代全量 10000 行）
@tool(name="task_log")
def task_log(pid: int, tail: int = 200):
    buffer = _BACKGROUND_PROCESSES[pid]["buffer"]
    return {"lines": buffer[-tail:]}
```

### 2. 动态工具加载策略

> 根据 LLM 能力自动选择最省 token 的工具传递方案。
> 核心原则：**高频工具永远预加载（不搜索），低频/长尾工具按需搜索。**

#### 两层分级

| 层 | 工具 | 数量 | 每轮 token | 是否需要 search |
|:--:|------|:----:|:----------:|:--------------:|
| **Layer 1 预加载** | read_file, write_file, search, bash, git, ask_choice | ~6 个 | ~500 | ❌ 永远可用 |
| **Layer 2 按需搜** | MCP 工具、web_search、ocr、extract_archive 等 | 无上限 | ~0（未搜索时） | ✅ 首次用才搜 |

Layer 1 是 AI 吃饭的碗，每轮都必须有。Layer 2 是 AI 偶尔用的螺丝刀，用的时候再搜。

#### 运行时协商

不硬编码模型名单，首次对话时让 LLM 自己协商，结果持久化到配置：

```python
# 高频工具：永远预加载，不检查协议
LAYER1_TOOLS = [
    ToolDef(name="read_file"), ToolDef(name="write_file"),
    ToolDef(name="search"), ToolDef(name="bash"),
    ToolDef(name="git"), ToolDef(name="ask_choice"),
]

class ToolExecutor:
    def __init__(self, model_adapter):
        self._protocol = None

    async def negotiate(self):
        cached = self._load_cached_protocol()
        if cached:
            self._protocol = cached
            return cached

        probe = await self._model.invoke([
            {"role": "system", "content": (
                "请选择工具交互协议（回复协议名即可）：\n"
                "1. native_mcp — 我自己管理工具清单，不需要你传工具描述\n"
                "2. search — 高频工具有，低频的自己搜\n"
                "3. full — 把所有工具描述都传给我"
            )},
            {"role": "user", "content": "请选择协议"},
        ], tools=[ToolDef(name="tool_search_tools",
                          description="搜索可用工具，返回 name+description+parameters")])

        if "native_mcp" in probe.content:
            self._protocol = "native_mcp"
        elif any(tc.name == "tool_search_tools" for tc in (probe.tool_calls or [])):
            self._protocol = "search_and_call"
        else:
            self._protocol = "full_schema"
        self._save_cached_protocol(self._protocol)
        return self._protocol

    def get_tool_definitions(self) -> list:
        """返回本轮传送给 LLM 的工具列表"""
        if self._protocol == "native_mcp":
            return []                              # 0 token，LLM 自己管
        if self._protocol == "search_and_call":
            return LAYER1_TOOLS + [                # ~500 tokens（Layer 1 高频工具）
                ToolDef(name="tool_search_tools"), # + 1 个搜索工具
                ToolDef(name="tool_call_direct"),
            ]
        return LAYER1_TOOLS + ALL_TOOLS            # 全量（含高频）

    async def execute(self, tool_call):
        if self._protocol == "search_and_call":
            if tool_call.name == "tool_search_tools":
                return self.search_tools(tool_call.args["query"])
            if tool_call.name == "tool_call_direct":
                return await self.call_tool(
                    tool_call.args["name"], tool_call.args.get("args", {}))
        return await self.call_tool(tool_call.name, tool_call.args)
```

#### 调 read_file 不需要搜索

```python
# search_and_call 模式下，Layer 1 工具已预加载
AI → read_file("config.py")         # 直接调，不搜
AI → bash("ls")                      # 直接调，不搜
AI → tool_search_tools("mcp_docker") # 第一次调 MCP 工具，搜
AI → tool_call_direct("mcp_docker...") # 调 MCP
# 后续再调 mcp_docker → 直接调，不搜
```

**预期节省**：

| 模型 | 当前 | 优化后 | 节省 |
|------|------|--------|------|
| DeepSeek V4 / Claude 3.5+（原生 MCP） | ~8000 tokens | **0** | **100%** |
| GPT-4o（search+call） | ~8000 tokens | **~200** | **~97%** |
| 旧模型（全量 fallback） | ~8000 tokens | ~8000 | 0% |

### 3. 工具结果缓存（同轮去重）

同一轮对话中 AI 可能重复调同一个工具（如反复 `read_file`）：

```python
_TOOL_CACHE: dict[str, str] = {}

async def execute(self, tool_call):
    cache_key = f"{tool_call.name}:{json.dumps(tool_call.args, sort_keys=True)}"
    if cache_key in _TOOL_CACHE:
        return _TOOL_CACHE[cache_key]  # 命中缓存，0 token
    result = await self._real_execute(tool_call)
    _TOOL_CACHE[cache_key] = result
    return result

def reset_tool_cache():
    _TOOL_CACHE.clear()  # 每轮开始前调用
```

> 只缓存同一轮内的重复调用，跨轮不缓存（文件可能已被修改）。

### 4. 工具并行执行

AI 同一轮发送多个 `tool_call` 时（如同时读 3 个文件），默认串行执行太慢：

```python
async def execute_batch(self, tool_calls: list[ToolCall]) -> list:
    """同一轮多个独立工具调用并行执行，互不依赖时提速显著"""
    async def safe_execute(tc):
        try:
            return await self._real_execute(tc)
        except Exception as e:
            return {"error": str(e)}

    return await asyncio.gather(
        *[safe_execute(tc) for tc in tool_calls]
    )
```

典型场景：
- AI 一次读多个文件：`read_file("a.py")` + `read_file("b.py")` + `read_file("c.py")` → **0.1s 而不是 0.3s**
- AI 同时搜多个关键词：`search("class User")` + `search("def login")` → **同时返回**
- AI 批量查 git：`git("status")` + `git("log -5")` → **同时返回**

> 依赖关系由 AI 自行保证——同轮 `tool_calls` 数组中的顺序不代表先后依赖。
> 如果 AI 需要先 A 再 B（如 B 依赖 A 的输出），它会分两轮调用，不会放一起。
