# 工具定义与设计

> **来源**: `architecture-refactor.md` §3.7.2, §3.8.7-3.8.9
> **关联文档**: `subprocess.md`（命令执行策略）、`backend-modules.md`（模块职责）、`folder-tree.md`（文件结构）
> 只涉及工具注册、参数设计、编辑策略。命令执行逻辑见 `subprocess.md`。

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

ToolExecutor 就是一条直连线：**收到 tool_call → 执行 → 原始结果返回给 AI**。

> 命令执行的具体策略（subprocess、沙箱、交互式处理）见 `subprocess.md`。

---

## 文件编辑方案

⚠️ **关键问题**：简单的 `old_str → new_str` 替换在复杂编辑场景下极易出错。

方案：不重新实现——使用市面上最成熟的方案。

### 方案一（推荐）：Aider 编辑引擎

```python
from aider.coders import Coder
from aider.io import InputOutput

class ToolFile:
    def __init__(self, workspace: str):
        self.io = InputOutput(yes=True)
        self.coder = Coder.create(
            ...  # 配置 edit_format="search-replace"
        )

    def edit_file(self, path: str, old_str: str, new_str: str) -> str:
        return self.coder.commands.cmd_edit(path, old_str, new_str)
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
    if result.returncode != 0:
        result = subprocess.run(
            ["git", "apply", "--3way", diff_path],
            capture_output=True, text=True
        )
    return result.stdout or result.stderr
```

### 方案三：基于代码图谱的结构化编辑（Graphify + tree-sitter）

不依赖文本匹配——Graphify 将代码解析为 AST 知识图谱，AI 通过实体名精确指定编辑位置。

### 三种方案对比

| 维度 | 方案一（Aider） | 方案二（git apply） | 方案三（Graphify + tree-sitter） |
|------|---------------|-------------------|-------------------------------|
| 原理 | 文本 search/replace + 模糊匹配 | unified diff + fuzz + 3-way | **AST 节点级结构化替换** |
| 准确性 | 较高（有 AST fallback） | 一般（纯文本） | **极高** |
| 速度 | 较慢 | **极快** | 中等 |
| 复杂度 | 中等 | **最低（2 行代码）** | 高 |
| 依赖 | `aider-chat` | 零 | `tree-sitter` + Graphify |
| 建议 | 生产环境 | **MVP 首选** | **长期目标** |

### 三种方案的集成路线

```
MVP（第 1 轮）:              方案二（git apply）
  ↓
第 2 轮:                    方案二 + Graphify（只读，代码搜索/理解）
  ↓
第 3 轮（长期目标）:        方案三（Graphify + tree-sitter 结构化编辑）
                            方案一（Aider）作为结构化编辑失败的 fallback
```

> 三者可以共存：`tool_patch_file.py` 内部三层 fallback——先结构化 AST 替换，失败则 Aider，再失败则 git apply。

### 策略模式重构建议

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

---

## `@tool` 自动注册（元编程）

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

# 使用示例
@tool(name="bash", category="system", timeout=30)
class ToolBash:
    async def __call__(self, cmd: str, cwd: str | None = None) -> str: ...

# ToolExecutor 自动从注册表加载
class ToolExecutor:
    def get_available_tools(self):
        return {name: cls() for name, cls in _TOOL_REGISTRY.items()}
```

**扩展步骤**：
```
1. 在 infrastructure/tools/ 对应分组下新建 tool_xxx.py
2. 用 @tool 装饰器注册
3. 不需要改前端 — 自动注册到 ToolNode
```

---

## 工具文件列表（按功能分组）

> 完整工具文件树见 `folder-tree.md` → `flypig/infrastructure/tools/`。

| 分组 | 工具 | 职责 |
|------|------|------|
| **file** | tool_read | ★ 读文件（支持 start/end 范围 / symbol 符号定位） |
| | tool_write | 写文件（新建/全量重写） |
| | tool_patch_file | ★ 局部更新：按 anchor 定位修改，省 90%+ token |
| | tool_delete | ★ 删除文件 |
| | tool_list_dir | ★ 目录浏览（deep=False 一层，deep=True 递归+统计） |
| **review** | tool_change_review | 变更审查数据生成 |
| | tool_lint | 代码规范检查（Ruff） |
| | tool_change_score | 变更影响评分 |
| **search** | tool_search | grep + find_files |
| | tool_search_tools | ★ 懒加载协议：按 query 搜索工具 schema |
| | tool_call_direct | ★ 懒加载协议：按名直接调工具 |
| | tool_web_search | ☆ P1 内置网络搜索（DuckDuckGo） |
| **interact** | tool_ask_choice | Explore 选择题 |
| **system** | tool_bash | subprocess 命令 |
| | tool_git | ★ Git 操作代替裸 bash |
| | tool_fetch_url | ★ 网页抓取（httpx，零依赖） |
| | tool_datetime | ★ 当前时间/时区/日期计算 |
| | tool_calc | ★ 安全数学计算 |
| | tool_task | task_status + task_list + task_log |
| | tool_task_manager | 任务看板：add_task / update_task / update_feedback |
| | tool_ocr | ☆ P1 OCR 文字识别 |
| | tool_extract_archive | 压缩解压 + Zip Slip 防护 |
| **mcp** | tool_mcp_loader | 加载 MCP 服务器并注册到 ToolNode |
| | tool_mcp_manager | MCP 自助安装 |

---

## 新增基础工具说明

| 工具 | 为什么必备 | 核心技术 |
|------|-----------|---------|
| `tool_git` | AI 每天几十次 git 操作，裸 bash git 结果混乱、idempotency 难保证 | `subprocess` 封装 git，结构化返回 |
| `tool_fetch_url` | 查文档、看 API 规格，不依赖 MCP fetch | `httpx`（Python 内置兼容） |
| `tool_list_dir` | 轻量目录浏览，替代 bash ls | `Path.iterdir()` |
| `tool_datetime` | AI 经常需要知道当前时间 | `datetime` 标准库 |
| `tool_calc` | 让 AI 算 token 数、文件大小、日期差 | `ast.literal_eval` + `Decimal` |

---

## 新增工具实现方案分析

| 工具 | 方案 | 代码量 | 依赖 |
|------|------|--------|------|
| `tool_datetime` | **自写** — `datetime.now()` + `pytz` | ~5 行 | 标准库 |
| `tool_calc` | **自写** — `ast.literal_eval` | ~15 行 | 可选 `numexpr` |
| `tool_list_dir` | **自写** — `Path.iterdir()` + `Path.rglob()` | ~20 行 | 标准库 |
| `tool_git` | **`GitPython` 薄封装** | ~60 行 | `pip install GitPython` |
| `tool_fetch_url` | **`httpx` + `trafilatura`** | ~30 行 | `pip install httpx trafilatura` |

**原则**：纯数据操作（时间/计算/扫描）自写，与外部系统交互（Git/HTTP）用成熟库封装。

---

## 工具参数优化：避免全量读写

| 工具 | 优化参数 | 对应场景 |
|------|---------|---------|
| `tool_read` | `start`/`end` → 按行范围读 | 搜到 def login 在 42-58 行 → 只读这一段 |
| `tool_write` | 本身全量写，无优化空间 | — |
| `tool_patch_file` | `anchor` → 按附近文本定位修改 | 不改完整文件 |
| `tool_search` | `pattern` + `glob` → 精确匹配 | 只搜 "def login" 不读全文件 |
| `tool_git` | `command` → git status/diff/log/commit 等 | 只取指定命令 |
| `tool_bash` | `max_output` → 输出截断 | 限制返回行数 |
| `task_log` | `tail` → 只取尾 N 行 | 不拿全量 10000 行缓冲区 |
| `tool_list_dir` | `deep` → True/False | 一层浏览 vs 递归扫描 |

### tool_read 和 tool_patch_file 详细设计

```python
@tool(name="read_file")
def read_file(path: str, start: int = None, end: int = None) -> dict:
    """读取文件内容。支持按行范围读取，避免全量 token 消耗。"""
    with open(path) as f:
        lines = f.readlines()
    if start is not None and end is not None:
        content = "".join(lines[start-1:end])
    elif start is not None:
        content = "".join(lines[start-1:])
    else:
        content = "".join(lines)
    return {"content": content, "lines": len(lines), "range": f"{start or 1}-{end or len(lines)}"}

@tool(name="patch_file")
def patch_file(path: str, operations: list[dict]) -> dict:
    """对文件做局部更新，不输出完整文件内容。比全量 write_file 省 90%+ token。"""
    with open(path) as f:
        lines = f.readlines()
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

---

## 工具与知识图谱/AST 的集成

当前工具是 AI 操作的**底层接口**，知识图谱和 AST 是上层**索引层**：

```
P0 纯工具:
AI 想理解项目结构:
  1. tool_list_dir(".", deep=True) → 文件树
  2. tool_search("class.*Service") → 搜服务类
  3. read_file("auth_service.py", start=1, end=50) → 读头部

P1 加上知识图谱:
AI 想理解项目结构:
  1. kg_query("list_classes") → {"ChatService": {"file":"chat.py"}}
  → 1 次查询，不需要逐文件搜索
```

### 工具的分层关系

```
┌─ 用户/对话 ──────────────────────────┐
│  ┌── AI ──────────────────────────┐   │
│  │  P1+ 优先调用:                  │   │
│  │  ├── kg_query("什么是 ChatService")│   │
│  │  └── vs_query("类似登录的功能")   │   │
│  │  查不到时降级:                    │   │
│  │  ├── search("ChatService")       │   │
│  │  ├── read_file("chat.py")        │   │
│  │  └── bash("grep -r ChatService") │   │
│  └──────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

---

## 幂等性（工具调用超时）

subprocess 超时后无法判断远程命令是否已执行，可能导致重复操作：

```
AI 调 bash("git commit -m 'fix'") → 超时 30s → AI 收到 TimeoutError
→ AI 重试 → 第二次成功 → 但第一次也成功了 → 两个重复的 commit
```

| 操作 | 是否幂等 | 说明 |
|------|---------|------|
| `git commit` | ❌ | 先检查 `git status` 是否有未提交变更 |
| `write_file` | ✅ | 写同样的内容 = 没变化 |
| `npm install` | ✅ | 重复安装不影响结果 |
| `mkdir -p` | ✅ | -p 参数保证 |
| `git push` | ❌ | 添加 `--force-with-lease` |

---

## 命令模式：工具调用可撤销

```python
class ToolCommand(ABC):
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
        self.backup = await read_file_content(self.path)
        await write_file(self.path, self.new_content)

    async def undo(self):
        if self.backup is not None:
            await write_file(self.path, self.backup)

class CommandHistory:
    """执行历史栈，支持撤销到任意点"""
    def __init__(self, max_undo=50):
        self._history: list[ToolCommand] = []
        self._max_undo = max_undo
        self._position = -1

    async def execute(self, cmd: ToolCommand):
        await cmd.execute()
        self._history = self._history[:self._position + 1]
        self._history.append(cmd)
        self._position += 1

    async def undo_to(self, target_index: int):
        while self._position >= target_index:
            await self._history[self._position].undo()
            self._position -= 1
```

> **关联文档**: `backend-modules.md`（CheckpointStore）、`adversarial-system.md`（驳回处理）

---

## Token 优化

### 1. 工具输出源头截断

```python
# tool_bash.py — subprocess 输出截断
@tool(name="bash")
def tool_bash(command: str, max_output: int = 5000):
    result = subprocess.run(command, capture_output=True, timeout=30)
    output = result.stdout[:max_output]
    if len(result.stdout) > max_output:
        output += b"\n...(truncated)..."
    return {"stdout": output.decode(), "stderr": result.stderr.decode()}

# task_log 默认只返回末尾 200 行
@tool(name="task_log")
def task_log(pid: int, tail: int = 200):
    buffer = _BACKGROUND_PROCESSES[pid]["buffer"]
    return {"lines": buffer[-tail:]}
```

### 2. 动态工具加载策略

#### 两层分级

| 层 | 工具 | 数量 | 每轮 token | 是否需要 search |
|:--:|------|:----:|:----------:|:--------------:|
| **Layer 1 预加载** | read_file, write_file, search, bash, git, ask_choice | ~6 个 | ~500 | ❌ |
| **Layer 2 按需搜** | MCP 工具、web_search、ocr、extract_archive 等 | 无上限 | ~0 | ✅ |

#### 运行时协商

```python
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
                "1. native_mcp\n"
                "2. search\n"
                "3. full"
            )},
            {"role": "user", "content": "请选择协议"},
        ], tools=[ToolDef(name="tool_search_tools",
                          description="搜索可用工具")])
        if "native_mcp" in probe.content:
            self._protocol = "native_mcp"
        elif any(tc.name == "tool_search_tools" for tc in (probe.tool_calls or [])):
            self._protocol = "search_and_call"
        else:
            self._protocol = "full_schema"
        self._save_cached_protocol(self._protocol)
        return self._protocol

    def get_tool_definitions(self) -> list:
        if self._protocol == "native_mcp":
            return []
        if self._protocol == "search_and_call":
            return LAYER1_TOOLS + [
                ToolDef(name="tool_search_tools"),
                ToolDef(name="tool_call_direct"),
            ]
        return LAYER1_TOOLS + ALL_TOOLS
```

**预期节省**：

| 模型 | 当前 | 优化后 | 节省 |
|------|------|--------|------|
| DeepSeek V4 / Claude 3.5+（原生 MCP） | ~8000 tokens | **0** | **100%** |
| GPT-4o（search+call） | ~8000 tokens | **~200** | **~97%** |
| 旧模型（全量 fallback） | ~8000 tokens | ~8000 | 0% |

### 3. 工具结果缓存（同轮去重）

```python
_TOOL_CACHE: dict[str, str] = {}

async def execute(self, tool_call):
    cache_key = f"{tool_call.name}:{json.dumps(tool_call.args, sort_keys=True)}"
    if cache_key in _TOOL_CACHE:
        return _TOOL_CACHE[cache_key]
    result = await self._real_execute(tool_call)
    _TOOL_CACHE[cache_key] = result
    return result

def reset_tool_cache():
    _TOOL_CACHE.clear()
```

> 只缓存同一轮内的重复调用，跨轮不缓存（文件可能已被修改）。

### 4. 工具并行执行

```python
async def execute_batch(self, tool_calls: list[ToolCall]) -> list:
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

> 依赖关系由 AI 自行保证——同一轮 `tool_calls` 数组中的顺序不代表先后依赖。

---

## 文件上传与压缩解压

前端 Element Plus Upload 组件（支持拖拽、多文件）→ `POST /api/upload` → 保存到工作区临时目录。

检测到压缩包（.zip/.7z/.tar/.rar）自动解压。`tool_extract_archive` 供 AI 直接调用：

```python
def _safe_extract_zip(archive: zipfile.ZipFile, target_dir: Path):
    for entry in archive.infolist():
        resolved = (target_dir / entry.filename).resolve()
        if not str(resolved).startswith(str(target_dir.resolve())):
            raise SecurityError(f"拒绝路径穿越: {entry.filename}")
        archive.extract(entry, target_dir)

def _safe_extract_tar(archive: tarfile.TarFile, target_dir: Path):
    for entry in archive.getmembers():
        resolved = (target_dir / entry.name).resolve()
        if not str(resolved).startswith(str(target_dir.resolve())):
            raise SecurityError(f"拒绝路径穿越: {entry.name}")
        archive.extract(entry, target_dir)

def tool_extract_archive(archive_path: str, target_dir: str = None) -> str:
    target = Path(target_dir or Path(archive_path).parent).resolve()
    ext = Path(archive_path).suffix.lower()
    extractors = {
        ".zip": lambda: _safe_extract_zip(zipfile.ZipFile(archive_path), target),
        ".tar": lambda: _safe_extract_tar(tarfile.open(archive_path), target),
        ".7z": lambda: py7zr.SevenZipFile(archive_path).extractall(target),
        ".rar": lambda: rarfile.RarFile(archive_path).extractall(target),
    }
    if ext not in extractors:
        raise ValueError(f"不支持的压缩格式: {ext}")
    try:
        extractors[ext]()
        return f"解压完成: {archive_path} -> {target}"
    except SecurityError as e:
        return f"解压失败 - 安全限制: {e}"
```

**安全要点**：Zip Slip 防护（检查解析后路径以目标目录开头）+ `.7z` 内置检查。依赖 `zipfile`/`tarfile`（标准库）+ `py7zr`/`rarfile`（可选）。

---

## OCR（光学字符识别，P1）

从图片中提取文字，用于扫描代码截图、PDF、白板照片等。

**技术选型**：PaddleOCR（国产，中英文效果好） > Tesseract（备选）

```python
# infrastructure/tools/system/tool_ocr.py
class ToolOCR:
    """AI 调用的 OCR 工具"""
    def __call__(self, image_path: str, lang: str = "ch+en") -> str:
        raise NotImplementedError("P1 实现，P0 走 vision 模型直接识图")
```

| 阶段 | 方案 | 说明 |
|------|------|------|
| **P0** | 不单独 OCR | 用 vision 模型直接看图 |
| **P1** | PaddleOCR | 大规模截图扫描，比 vision 模型便宜 100 倍 |
| **P2** | OCR + LLM 级联 | 处理模糊/手写场景 |

---

## 图片理解（Vision）

AI 直接看到图片内容，不走 OCR 中间层。

**原理**：前端将图片转为 base64 data URL，拼接在 user message 中传给 vision 模型。

```python
# 前端消息格式
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "这个报错是什么意思？"},
        {"type": "image", "image": "data:image/png;base64,..."},
    ]
}

# 后端处理（chat_node 中）
for part in user_message.content:
    if part["type"] == "image":
        if not model_supports_vision(state["model"]):
            text = tool_ocr(part["image"])
            part = {"type": "text", "text": f"[图片OCR结果]:\n{text}"}
```

| 模型 | 支持视觉 |
|------|---------|
| DeepSeek-VL2 | ✅ |
| GPT-4o | ✅ |
| Claude 3.5 Sonnet | ✅ |
| DeepSeek-Chat (V3) | ❌ 自动降级 OCR |
| Qwen-VL | ✅ |

---

## 内置搜索（非 MCP 依赖，P1）

当前搜索依赖 MCP `web-search` 服务器（需 Node.js），P1 改用 `duckduckgo-search` pip 包：

```python
# infrastructure/tools/search/tool_web_search.py
class ToolWebSearch:
    def __call__(self, query: str, max_results: int = 5) -> str:
        raise NotImplementedError("P1 实现，P0 依赖 MCP web-search")
```

| 阶段 | 方案 | 依赖 | API Key |
|------|------|------|---------|
| **P0** | MCP web-search | Node.js | ❌ |
| **P1** | DuckDuckGo（`duckduckgo-search`） | 零 | ❌ |
| **P2** | SerpAPI / Bing Search API | 可选 | ✅ |
