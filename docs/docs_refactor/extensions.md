# 扩展预留

> **来源**: `architecture-refactor.md` §3.7, §3.9
> **关联文档**: `backend-modules.md`（接口定义）、`subprocess-and-tools.md`（MCP 工具）、`usage-tracking.md`（用量追踪系统）
> 当前只定义接口 + 空实现，不实现具体逻辑。

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
