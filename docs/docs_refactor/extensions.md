# 扩展预留

> **来源**: `architecture-refactor.md` §3.7, §3.9
> **关联文档**: `backend-modules.md`（接口定义）、`tools.md`（MCP 工具）、`usage-tracking.md`（用量追踪系统）、`plan-task-system.md`（任务管理系统）、`resilience.md`（许可/更新/导出接口）
> 当前只定义接口 + 空实现(NoOp)，不实现具体逻辑。P1/P2 阶段再做完整实现。

## MCP 协议集成

### 三层策略：基础配置 → AI 按需发现 → 自动安装

**第一层：基础配置（项目自带，开箱即用）**

项目默认附带 `mcp.json`，预装最常用的 MCP 服务器，用户零操作即可使用：

```json
{
  "mcpServers": {
    "web-search": {"command": "npx", "args": ["@anthropic/mcp-server-web-search"]},
    "fetch": {"command": "npx", "args": ["@anthropic/mcp-server-fetch"]}
  }
}
```

`mcp_loader.py` 启动时自动加载此文件，连接 MCP 服务器，将 tools 注册到 LangGraph ToolNode。

**第二层 + 第三层：AI 按需发现 + 自动安装（用现成方案）**

不自研注册表和安装逻辑——直接使用 `mcp-auto-install`（`pip install mcp-auto-install`）。

`mcp-auto-install` 是一个 MCP 服务器，让 AI 通过自然语言发现、安装和管理其他 MCP 服务器：

```
AI 遇到需要搜索网页但没装搜索能力：
  → 调用 mcp-auto-install 提供的 install_mcp_server 工具
  → mcp-auto-install 自动搜索官方 MCP Registry
  → 找到 @anthropic/mcp-server-web-search
  → 用户[批准] → 自动下载安装 + 写入 mcp.json
  → mcp_loader 热加载 → 注册到 ToolNode
  → AI 立即可用
```

| 能力 | 手写方案 | mcp-auto-install |
|------|---------|----------------|
| 搜索注册表 | 手写 `_MCP_REGISTRY` 字典 | 搜索**官方 MCP Registry**（registry.modelcontextprotocol.io） |
| 安装执行 | 仅提示命令字符串 | 自动 npm/pip 安装 + 写 mcp.json |
| 服务器范围 | 限于内置 6 个 | 官方 Registry 全部服务器 |
| 维护成本 | 需手动更新注册表 | 社区维护，自动更新 |

配置方式：在 `mcp.json` 中添加 `mcp-auto-install` 作为标准 MCP 服务器：

```json
{
  "mcpServers": {
    "web-search": {"command": "npx", "args": ["@anthropic/mcp-server-web-search"]},
    "fetch": {"command": "npx", "args": ["@anthropic/mcp-server-fetch"]},
    "auto-install": {"command": "npx", "args": ["@anthropic/mcp-auto-install"]}
  }
}
```

AI 就可以通过自然语言按需安装任何 MCP 服务器，无需用户手动操作。

> **安全**：mcp-auto-install 安装时弹审批卡片，显示服务器信息，用户批准后才执行安装。

## 文件上传与压缩解压（§3.7.2）

文件上传前后端联动，用户在 Web Dashboard 拖拽/选择文件上传：

```
前端: Element Plus Upload 组件（支持拖拽、多文件、大文件分片）
后端: POST /api/upload → 保存到工作区临时目录
  → 检测到压缩包（.zip/.7z/.tar/.rar）→ 自动解压到同目录
  → 返回文件列表给前端

AI: 上传完成后自动感知新文件，可读取/分析
```

压缩解压工具（`tool_extract_archive` 供 AI 直接调用）：

```python
def _safe_extract_zip(archive: zipfile.ZipFile, target_dir: Path):
    """安全解压 zip，防止 zip slip 路径穿越"""
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
    """自动识别格式并安全解压（防路径穿越攻击）"""
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

**安全要点**：
- Zip Slip 防护：检查每个条目解析后的绝对路径是否以目标目录开头
- `.7z` 文件：py7zr >= 0.20 已有内置安全检查
- 依赖 `zipfile`/`tarfile`（标准库）+ `py7zr`/`rarfile`（可选）

## 对话存储（IConversationStore）

> 替代原来散落的 IRepository / IHistoryStore / CheckpointStore。一份数据 + 多种查询视角。

### 数据模型

```python
# domain/interfaces/iconversation_store.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SuggestionItem:
    id: str
    text: str
    rule_name: str
    adopted: bool | None       # None=未反馈, True=采纳, False=拒绝
    feedback_timestamp: datetime | None

@dataclass
class TurnRecord:
    """一轮对话的完整记录"""
    session_id: str
    turn_id: int
    user_message: str
    ai_response: str
    tool_calls: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    mode: str = "execute"
    persona: str = "developer"
    summary: str | None = None
    cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: list = field(default_factory=list)
    git_commit_hash: str | None = None
    suggestions: list = field(default_factory=list)
    change_review: dict | None = None
    change_score: dict | None = None
```

### 任务数据类

```python
# domain/models/task.py（新增）
@dataclass
class TaskItem:
    """任务项"""
    id: str
    session_id: str
    title: str
    status: str                        # pending / in_progress / blocked / cancelled / completed
    created_turn: int
    status_turn: int | None = None
    cancelled_reason: str | None = None
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None

@dataclass
class TaskStatusChange:
    """任务状态变更记录"""
    task_id: str
    turn_id: int
    old_status: str | None
    new_status: str
    reason: str | None = None
    changed_at: datetime | None = None

@dataclass
class TaskStats:
    """任务统计（Dashboard 用）"""
    total: int
    pending: int
    in_progress: int
    blocked: int
    cancelled: int
    completed: int
```

### 接口

```python
class IConversationStore(ABC):
    """统一对话存储——只存原始数据，不压缩。压缩是 IContextPipeline 的职责。"""

    @abstractmethod
    async def save_turn(self, session_id: str, turn_id: int, data: TurnRecord): ...

    @abstractmethod
    async def get_recent_turns(self, session_id: str, limit: int = 20) -> list[TurnRecord]:
        """最近 N 轮完整对话（给 pipeline 的原材料）"""

    @abstractmethod
    async def get_summaries(self, session_id: str, limit: int = 50) -> list[TurnRecord]:
        """所有轮次的摘要列表（给 pipeline 拼 system prompt）"""

    @abstractmethod
    async def search(self, query: str, session_id: str | None = None) -> list[TurnRecord]:
        """按内容/标签搜索对话"""

    @abstractmethod
    async def get_checkpoint(self, session_id: str, turn_id: int) -> str | None:
        """获取指定轮次的 git commit_hash"""

    @abstractmethod
    async def update_suggestion_feedback(self, suggestion_id: str, adopted: bool): ...

    @abstractmethod
    async def list_sessions(self, user_id: str, limit: int = 20) -> list[SessionMeta]: ...

    @abstractmethod
    async def delete_session(self, session_id: str): ...

    # ======== Task CRUD（详见 plan-task-system.md）========

    @abstractmethod
    async def add_task(self, session_id: str, turn_id: int, title: str,
                       sort_order: int = 0) -> str:
        """添加任务到会话，返回 task_id"""

    @abstractmethod
    async def update_task_status(self, task_id: str, new_status: str,
                                  turn_id: int, reason: str = None):
        """更新任务状态 + 记录 status_log"""

    @abstractmethod
    async def get_session_tasks(self, session_id: str) -> list[TaskItem]:
        """获取会话全部任务"""

    @abstractmethod
    async def get_tasks_at_turn(self, session_id: str, turn_id: int) -> list[TaskItem]:
        """恢复到某 turn 时的任务状态快照（回溯用）"""

    @abstractmethod
    async def search_tasks(self, session_id: str = None,
                           query: str = "", status: str = None) -> list[TaskItem]:
        """跨会话搜索任务"""

    @abstractmethod
    async def get_task_stats(self, session_id: str = None) -> TaskStats:
        """任务统计"""

    @abstractmethod
    async def get_task_history(self, task_id: str) -> list[TaskStatusChange]:
        """单个任务完整状态变更历史"""
```

### 实现演进

| 阶段 | 实现 | 存储 | 检索方式 |
|------|------|------|---------|
| **P0** | `SqliteConversationStore` | SQLite 单表 | `turn_id`/`timestamp` 排序 + `LIKE` 搜索 |
| **P1** | 升级 SQLite | SQLite + FTS5 索引 | 全文搜索 + tag 精确匹配 |
| **P2** | `PgConversationStore` | PostgreSQL + pgvector | 向量检索 + 混合搜索（SaaS 多租户） |

### 存储策略

原始数据**全部保留，不删**。但超过 `max_full_turns`（默认 20）的轮次：
- `user_message` / `ai_response` / `tool_results` 清空
- `summary` / `tags` / `suggestions` / `cost` 等元数据保留
- 所以 `get_summaries()` 永远能拿到全部轮次的概要

## 上下文压缩（IContextPipeline）

> 在调 LLM 之前，把原始消息压缩到 token 预算以内。不存储，只转换。

```python
class IContextPipeline(ABC):
    @abstractmethod
    async def build(
        self,
        store: IConversationStore,
        session_id: str,
        user_input: str,
        budget: int = 100_000,
    ) -> list:
        """返回压缩后的消息列表，直接喂给 LLM"""

class ICompressLayer(ABC):
    @abstractmethod
    def compress(self, messages: list, budget: int) -> list: ...

class CompositePipeline(IContextPipeline):
    def __init__(self, layers: list[ICompressLayer]):
        self.layers = layers

    async def build(self, store, session_id, user_input, budget=100_000):
        recent = await store.get_recent_turns(session_id, 20)
        summaries = await store.get_summaries(session_id, 50)
        messages = self._assemble(recent, summaries, user_input)
        for layer in self.layers:
            if count_tokens(messages) <= budget:
                break
            messages = layer.compress(messages, budget)
        return messages
```

### 内置三层

| 层 | 代码量 | 做什么 | 优先级 |
|----|--------|--------|--------|
| `TruncateResultsLayer` | ~20 行 | 工具结果 > 2000 字截断保留头尾 | 第一层 |
| `FoldOldTurnsLayer` | ~30 行 | 最早几轮折叠成摘要，保留最近 N 轮完整 | 第二层 |
| `TrimMessagesLayer` | 1 行 | 包装 LangGraph 的 `trim_messages` 做保底 | 第三层 |

### Token 优化扩展点

#### 动态 token 预算

当前 `budget=100_000` 是硬编码值。改为根据模型上下文窗口动态调整：

```python
MODEL_TOKEN_BUDGETS = {
    "deepseek-v3":  80_000,   # 留 30% 给输出
    "gpt-4o":      100_000,
    "claude-3.5":  150_000,
    "local":        32_000,
}

def get_budget(model: str) -> int:
    return int(MODEL_TOKEN_BUDGETS.get(model, 100_000) * 0.7)
```

#### AI 输出 token 预算

`chat_node` 中限制单次回复长度：

```python
# chat_node
response = llm.invoke(
    messages,
    max_tokens=OUTPUT_BUDGETS.get(state["mode"], 4096),
    # Explore: 2048, Plan: 4096, Execute: 8192
)
```

#### 语义级工具结果摘要（P2 扩展）

当前 `TruncateResultsLayer` 做头尾截断。P2 时可用 LLM 提取关键信息：

```python
class AiSummaryLayer(ICompressLayer):
    """用 LLM 总结工具结果，替代机械截断"""
    def compress(self, messages, budget):
        for msg in messages:
            if msg["role"] == "tool" and len(msg["content"]) > 2000:
                msg["content"] = self._summarize(msg["content"])
        return messages
```

### 工具描述按使用频率排序

Execute 模式下全部工具的描述列表会随 MCP 持续膨胀。按使用频率排序+折叠：

```python
# executor.py — 工具描述频率排序
TOOL_CALL_FREQUENCY: dict[str, int] = defaultdict(int)

def get_tool_definitions(all_tools: list) -> list:
    """前 5 个完整描述，后面的只传 name"""
    all_tools.sort(key=lambda t: -TOOL_CALL_FREQUENCY.get(t.name, 0))
    return all_tools[:5] + [
        ToolDef(name=t.name) for t in all_tools[5:]
    ]

# 每次工具调用后更新频率
def record_tool_call(name: str):
    TOOL_CALL_FREQUENCY[name] += 1
```

### 对话历史去重 `DedupLayer`

同一用户输入重复出现时（如连续两次"帮我看下认证"），第二轮不需要 AI 再看一遍自己的完整回复：

```python
class DedupLayer(ICompressLayer):
    """移除对话历史中重复的用户输入（不降质量）"""
    def __init__(self):
        self._seen = set()

    def compress(self, messages, budget):
        for msg in messages:
            if msg["role"] == "user" and msg["content"] in self._seen:
                msg["content"] = "[同上轮]"  # 替换为标记
            elif msg["role"] == "user":
                self._seen.add(msg["content"])
        return messages
```

### 旧轮工具结果→摘要 `ToolResultSummaryLayer`

当 AI 第 3 轮还在引用第 1 轮的工具结果时，原始内容很长但 AI 实际只用了其中一小部分：

```python
class ToolResultSummaryLayer(ICompressLayer):
    """超过 N 轮的工具结果替换为摘要（长对话省 20-40%）"""
    def __init__(self, max_age_turns: int = 5):
        self.max_age = max_age_turns

    def compress(self, messages, budget):
        turn_count = 0
        for msg in reversed(messages):
            if msg["role"] in ("user", "assistant"):
                turn_count += 1
            if msg["role"] == "tool" and turn_count > self.max_age:
                msg["content"] = f"[工具结果摘要：{self._brief(msg['content'])}]"
        return messages

    def _brief(self, text: str) -> str:
        return text[:100].replace("\n", " ") + "..." if len(text) > 100 else text
```

> **不实现 AI 回复缓存**：agent 场景中文件状态会变化，两次相同问题的上下文可能完全不同。缓存带来的风险（返回过时答案）远大于收益（省 token）。

### 与 ConversationStore 的关系

```
chat_node:
    1. pipeline.build(store, session_id, input)    ← 读 store，压缩
    2. response = llm.invoke(compressed)
    3. store.save_turn(session_id, turn_id, data)   ← 写 store
```

Pipeline 只读，Store 只存。职责清晰。

## LangMem 集成（P2 选项）

LangMem 不是 ConversationStore 的替代品，而是**额外的知识层**——AI 主动调用的工具。

### 和 ConversationStore 的对比

| 维度 | ConversationStore | LangMem |
|------|-----------------|---------|
| 存什么 | 对话记录（user_msg + tool_results） | 知识片段（"用户喜欢 FastAPI"） |
| 谁写 | 系统自动：每轮 `save_turn()` | AI 主动调 `manage_memory()` |
| 谁读 | Pipeline 自动读 → 压缩 → 喂 LLM | AI 主动调 `search_memory()` |
| 写入频率 | 每轮 1 次 | AI 觉得有必要时才写 |
| 检索 | turn_id/timestamp/summary 索引 | 向量嵌入 + 语义搜索 |
| 数据量 | 全部对话（可能很大） | 精选知识点（轻量） |

### 集成方式

```python
# 注册到 ToolNode，仅 Execute 模式可用
from langmem import create_manage_memory_tool, create_search_memory_tool

memory_tools = [
    create_manage_memory_tool(
        namespace=("memories",),
        store=store_backend,  # InMemoryStore / AsyncPostgresStore
    ),
    create_search_memory_tool(
        namespace=("memories",),
        store=store_backend,
    ),
]
```

AI 会在对话中**自行决定**何时调用：

```
用户: "还是按上次说的那个方案"
  AI 调 search_memory("上次说的方案") → "用户偏好 FastAPI + SQLite"
  AI 参考后回答

用户: "记住，我喜欢用 Pydantic"
  AI 调 manage_memory("用户喜欢用 Pydantic")
```

### 实现演进

| 阶段 | 方式 | 说明 |
|------|------|------|
| **P0（MVP）** | 不用 LangMem | ConversationStore 的 get_recent_turns 已经够用 |
| **P1（有用户）** | LangMem + SQLite | AI 能查/存知识点，后台自动提取 |
| **P2（向量库）** | LangMem + pgvector | 语义搜索精度大幅提升 |

> LangMem 不是架构依赖。`IConversationStore.search()` 是对历史对话的全文/向量搜索，LangMem 是对"提炼后的知识片段"的搜索，两者独立。

## IKnowledgeStore（代码知识图谱）

```python
class IKnowledgeStore(ABC):
    async def index_project(project_root) -> None: ...
    async def search_entity(name, type) -> list[EntityLocation]: ...
    async def get_entity_relations(entity_name) -> list[Relation]: ...
    async def get_file_summary(file_path) -> FileSummary: ...
```

---

## 多模态与感知工具

### OCR（光学字符识别）

从图片中提取文字，用于扫描代码截图、PDF、白板照片等。

**技术选型**：PaddleOCR（国产，中英文效果好） > Tesseract（备选）

```python
# infrastructure/tools/system/tool_ocr.py
class ToolOCR:
    """AI 调用的 OCR 工具"""

    def __call__(self, image_path: str, lang: str = "ch+en") -> str:
        """
        从图片中提取文字。
        支持: png/jpg/webp/bmp
        返回: 提取的纯文本（含行号）
        """
        # P0: 将 base64 图片写入临时文件 → 调 OCR 引擎 → 返回文本
        # P1: 流式识别大图
        raise NotImplementedError("P1 实现，P0 走 vision 模型直接识图")
```

| 阶段 | 方案 | 说明 |
|------|------|------|
| **P0** | 不单独 OCR | 用 vision 模型直接看图（DeepSeek-VL / GPT-4o / Claude 3.5） |
| **P1** | PaddleOCR | 大规模截图扫描场景，比 vision 模型便宜 100 倍 |
| **P2** | OCR + LLM 级联 | OCR 提取 → LLM 理解上下文，处理模糊/手写场景 |

### 图片理解（Vision）

AI 直接看到图片内容，不走 OCR 中间层。

**原理**：前端将图片转为 base64 data URL，拼接在 user message 中传给 vision 模型。

```python
# 前端 → 后端的消息格式（Vercel AI SDK 扩容）
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "这个报错是什么意思？"},
        {"type": "image", "image": "data:image/png;base64,..."},
    ]
}
```

**后端处理**：

```python
# chat_node 中检测 image 类型的 content
for part in user_message.content:
    if part["type"] == "image":
        # 多模态模型原生支持 → 直接传
        # 纯文本模型 → 调 tool_ocr 提取文字替代
        if not model_supports_vision(state["model"]):
            text = tool_ocr(part["image"])
            part = {"type": "text", "text": f"[图片OCR结果]:\n{text}"}
```

| 模型 | 支持视觉 | 说明 |
|------|---------|------|
| DeepSeek-VL2 | ✅ | 国产首选 |
| GPT-4o | ✅ | OpenAI |
| Claude 3.5 Sonnet | ✅ | Anthropic |
| DeepSeek-Chat (V3) | ❌ | 纯文本，自动降级 OCR |
| Qwen-VL | ✅ | 阿里通义千问视觉版 |

### 内置搜索（非 MCP 依赖）

当前搜索完全依赖 MCP `web-search` 服务器，用户需要装 `npx`。**单机软件不应该强制依赖 Node.js。**

```python
# infrastructure/tools/search/tool_web_search.py
class ToolWebSearch:
    """内置网络搜索，零外部依赖"""

    def __call__(self, query: str, max_results: int = 5) -> str:
        """
        搜索网络信息。
        策略:
          P0: 走 searxng 自托管 或 DuckDuckGo（无需 API Key）
          P1: 走 SerpAPI / Bing Search API（用户配置 Key）
          P2: MCP web-search（高级功能）
        """
        raise NotImplementedError("P1 实现，P0 依赖 MCP web-search")
```

| 阶段 | 方案 | 依赖 | API Key 需要 |
|------|------|------|-------------|
| **P0** | MCP web-search（已有） | Node.js + npx | ❌ |
| **P1** | **DuckDuckGo**（`duckduckgo-search` pip 包） | 零 | ❌ |
| **P2** | SerpAPI / Bing Search API | 用户配置可选 | ✅ |

---

## P1/P2 预留接口（详见 resilience.md）

当前阶段用 NoOp 实现，不侵入主流程。以下接口只为未来预留 API 形态。

### ILicenseService（P2 — 许可激活）

```python
# domain/interfaces/ilicense_service.py
class ILicenseService(ABC):
    @abstractmethod
    async def check_license(self) -> LicenseStatus: ...
    @abstractmethod
    async def activate(self, license_key: str) -> ActivationResult: ...
    @abstractmethod
    async def deactivate(self) -> bool: ...

@dataclass
class LicenseStatus:
    is_valid: bool
    license_type: str = "trial"
    days_remaining: int = 0
    expires_at: str | None = None

@dataclass
class ActivationResult:
    success: bool
    message: str
    machine_id: str | None = None

class NoOpLicenseService(ILicenseService):
    """MVP 阶段 — 永远返回「已激活」"""
    async def check_license(self) -> LicenseStatus:
        return LicenseStatus(is_valid=True, license_type="pro", days_remaining=36500)
    async def activate(self, key: str) -> ActivationResult:
        return ActivationResult(True, "已激活（MVP 模式）", "noop-mvp")
    async def deactivate(self) -> bool:
        return True
```

### IUpdateService（P2 — 自动更新）

```python
# domain/interfaces/iupdate_service.py
class IUpdateService(ABC):
    @abstractmethod
    async def check_update(self) -> UpdateInfo | None: ...
    @abstractmethod
    async def download_and_install(self, update_id: str) -> bool: ...
    @abstractmethod
    async def get_update_history(self) -> list[UpdateRecord]: ...

@dataclass
class UpdateInfo:
    version: str
    release_date: str
    changelog: str
    download_url: str
    checksum: str
    size_mb: float
    is_forced: bool = False

@dataclass
class UpdateRecord:
    version: str
    installed_at: str
    success: bool

class NoOpUpdateService(IUpdateService):
    """MVP 阶段 — 永远返回「已是最新」"""
    async def check_update(self) -> UpdateInfo | None: return None
    async def download_and_install(self, update_id: str) -> bool: return False
    async def get_update_history(self) -> list[UpdateRecord]: return []
```

### ExportService（P1 — 导入导出）

```python
# application/services/export_service.py
class ExportService:
    """P0 只定义方法签名，全部 raise NotImplementedError"""
    async def export_chat(self, session_id: str, format: str = "markdown") -> str:
        raise NotImplementedError("P1 实现")
    async def export_tasks(self, session_id: str) -> str:
        raise NotImplementedError("P1 实现")
    async def import_from_claude(self, path: str) -> str:
        raise NotImplementedError("P2 实现")
    async def import_from_codebuddy(self, path: str) -> str:
        raise NotImplementedError("P2 实现")
```

### ModelFallbackService（P1 — 多模型自动切换）

```python
# orchestration/model_fallback_service.py
class ModelFallbackService:
    """P0: 不切换，仅记录错误。P1: 自动 fallback 到备选模型"""
    def get_available_models(self) -> list[str]:
        return [Container.get("config").default_model]
    async def fallback_if_needed(self, model_name: str, error: Exception) -> str | None:
        logger.warning("模型 [{}] 失败: {}（P0 不自动 fallback）", model_name, error)
        return None
```
