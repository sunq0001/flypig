# mem_convStore：对话存储总览

> **历史来源**: `architecture_refactor_old.md` §3.7, §3.9
> **关联文档**: `mem_convStore_tasks.md`（任务）、`mem_convStore_usage.md`（用量）、`mem_convStore_checkpoints.md`（Checkpoint）、`short-term-memory.md`（上下文压缩）

## 数据文件

`data/conversations.db`（SQLite WAL 模式）

## 所有表

| # | 表 | 用途 | 子文档 |
|:-:|:--:|------|:------:|
| 1 | `sessions` | 会话元数据 | —（本文件） |
| 2 | `turns` | 对话轮次 | —（本文件） |
| 3 | `tasks` | 任务列表 | `mem_convStore_tasks.md` |
| 4 | `task_status_log` | 任务状态变更历史 | `mem_convStore_tasks.md` |
| 5 | `suggestions` | 对抗建议反馈 | —（本文件） |
| 6 | `turn_usage` | 每轮用量聚合 | `mem_convStore_usage.md` |
| 7 | `call_usage` | 每次调用明细 | `mem_convStore_usage.md` |
| 8 | `model_pricing` | 模型价格快照 | `mem_convStore_usage.md` |
| 9 | `checkpoint_mappings` | turn_id → git commit_hash | `mem_convStore_checkpoints.md` |
| 10 | `code_graph` | 代码关系网络（P1） | —（本文件） |

## 数据关系

```
conversations.db
┌─────────────────────────────────────────────────────┐
│  sessions (会话管理)                                  │
│    └── turns (对话轮次)                               │
│         每个 turn 关联:                                │
│          ├── tasks + task_status_log                 │
│          ├── suggestions (对抗建议)                    │
│          ├── turn_usage + call_usage (用量)            │
│          ├── model_pricing (价格快照)                  │
│          └── checkpoint_mappings (git hash)           │
│                                                       │
│  code_graph (P1，代码关系网络)                          │
└─────────────────────────────────────────────────────┘
```

## 表结构（无子文档的表）

### sessions

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,             -- session_001
    user_id TEXT NOT NULL,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP,
    turn_count INTEGER DEFAULT 0,
    workspace TEXT
);
CREATE INDEX idx_sessions_user ON sessions(user_id);
```

### turns

```sql
CREATE TABLE turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    user_message TEXT,
    ai_response TEXT,
    tool_calls TEXT,             -- JSON
    tool_results TEXT,           -- JSON
    mode TEXT DEFAULT 'execute',
    persona TEXT DEFAULT 'developer',
    summary TEXT,
    tags TEXT,                   -- JSON
    cost REAL DEFAULT 0.0,
    git_commit_hash TEXT,
    timestamp TEXT NOT NULL,
    partial INTEGER DEFAULT 0,   -- 1 = 未正常结束
    UNIQUE(session_id, turn_id)
);
CREATE INDEX idx_turns_session ON turns(session_id);
CREATE INDEX idx_turns_timestamp ON turns(timestamp);
```

### suggestions

```sql
CREATE TABLE suggestions (
    id TEXT PRIMARY KEY,
    turn_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    text TEXT NOT NULL,
    rule_name TEXT,
    adopted INTEGER,                 -- 0=拒绝, 1=采纳, NULL=未反馈
    feedback_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### code_graph（P1 新增）

```sql
CREATE TABLE code_graph (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    relations TEXT,              -- JSON
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_code_entity ON code_graph(entity_name);
CREATE INDEX idx_code_file ON code_graph(file_path);
```

## 数据类

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class TurnRecord:
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
    change_review: dict | None = None
    change_score: dict | None = None

@dataclass
class SuggestionItem:
    id: str
    text: str
    rule_name: str
    adopted: bool | None          # None=未反馈, True=采纳, False=拒绝
    feedback_timestamp: datetime | None
```

## 接口

所有接口定义在 `domain/interfaces/`：

| 接口 | 文件 | 说明 |
|:----:|:----:|:----:|
| `IConversationStore` | `iconversation_store.py` | 核心存储接口 |
| `IUsageTracker` | `iusage_tracker.py` | 用量追踪接口 |
| `IKnowledgeGraph` | `iknowledge_graph.py` | 代码知识图谱（P1） |

### IConversationStore

```python
class IConversationStore(ABC):
    @abstractmethod
    async def save_turn(self, session_id: str, turn_id: int, data: TurnRecord): ...
    @abstractmethod
    async def get_recent_turns(self, session_id: str, limit: int = 20) -> list[TurnRecord]: ...
    @abstractmethod
    async def get_summaries(self, session_id: str, limit: int = 50) -> list[TurnRecord]: ...
    @abstractmethod
    async def search(self, query: str, session_id: str | None = None) -> list[TurnRecord]: ...
    @abstractmethod
    async def list_sessions(self, user_id: str, limit: int = 20) -> list[SessionMeta]: ...
    @abstractmethod
    async def delete_session(self, session_id: str): ...
    # 任务方法 → mem_convStore_tasks.md
    # checkpoint 方法 → mem_convStore_checkpoints.md
```

### IUsageTracker → `mem_convStore_usage.md`

### IKnowledgeGraph（P1）

```python
class IKnowledgeGraph(ABC):
    async def index_project(project_root) -> None: ...
    async def search_entity(name, type) -> list[EntityLocation]: ...
    async def get_entity_relations(entity_name) -> list[Relation]: ...
    async def get_file_summary(file_path) -> FileSummary: ...
```

## LangMem 集成（P2 选项）

LangMem 不是 ConversationStore 的替代品，而是额外的知识层——AI 主动调用的工具。

| 维度 | ConversationStore | LangMem |
|------|-----------------|---------|
| 存什么 | 对话记录 + 任务 + 用量 | 知识片段 |
| 谁写 | 系统自动 | AI 主动调 `manage_memory()` |
| 检索 | turn_id / 全文 | 向量嵌入 + 语义搜索 |

```python
from langmem import create_manage_memory_tool, create_search_memory_tool
memory_tools = [
    create_manage_memory_tool(namespace=("memories",), store=store_backend),
    create_search_memory_tool(namespace=("memories",), store=store_backend),
]
```

P0 不启用，P1 有用户后再集成。

## 存储策略

原始数据全部保留不删。超过 `max_full_turns`（默认 20）的轮次清空 `user_message` / `ai_response` / `tool_results`，保留 `summary` 等元数据。

## 实现演进

| 阶段 | 实现 | 存储 | 检索方式 |
|------|------|------|---------|
| **P0** | `SqliteConversationStore` | SQLite 单表 | turn_id 排序 + LIKE |
| **P1** | SQLite + FTS5 | 全文搜索 | tag 精确匹配 |
| **P2** | `PgConversationStore` | PostgreSQL + pgvector | 混合搜索 |
