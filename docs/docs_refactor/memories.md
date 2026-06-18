# 长期记忆系统（Memories）

> **来源**: `architecture-refactor.md` §3.7, §3.9
> **关联文档**: `short-term-memory.md`（上下文压缩）、`backend-modules.md`（DI 注册）、`api-reference.md`（查询端点）
> 所有持久化数据的统一描述：对话记录、任务、用量、checkpoint、反馈。

## 概述

长期记忆统一存储在 `conversations.db`（SQLite WAL 模式），共 7 张表：

| 表 | 用途 | 写入者 |
|:--:|------|:------:|
| `turns` | 对话轮次（含 partial 标记） | ConversationStore |
| `tasks` | 任务列表（含 user_feedback） | AI（tool_add_task） |
| `task_status_log` | 任务状态变更历史 | ConversationStore |
| `turn_usage` | 每轮用量聚合 | SqliteUsageTracker |
| `call_usage` | 每次调用明细 | SqliteUsageTracker |
| `model_pricing` | 模型价格快照（每日） | PricingFetcher |
| `checkpoint_mappings` | turn_id → git commit_hash（回溯用） | GitCheckpointManager |

---

## 对话存储（ConversationStore）

> 替代原来散落的 IRepository / IHistoryStore / CheckpointStore。

### 表 1：`turns`

```sql
CREATE TABLE turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    user_message TEXT,
    ai_response TEXT,
    tool_calls TEXT,              -- JSON 数组
    tool_results TEXT,            -- JSON 数组
    mode TEXT DEFAULT 'execute',  -- explore / plan / execute
    persona TEXT DEFAULT 'developer',
    summary TEXT,
    tags TEXT,                    -- JSON 数组
    cost REAL DEFAULT 0.0,
    git_commit_hash TEXT,
    timestamp TEXT NOT NULL,       -- ISO8601
    partial INTEGER DEFAULT 0,    -- 1 = 未正常结束（崩溃恢复用）
    UNIQUE(session_id, turn_id)
);
CREATE INDEX idx_turns_session ON turns(session_id);
CREATE INDEX idx_turns_timestamp ON turns(timestamp);
```

### 数据类

```python
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
```

### 接口

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
```

### 存储策略

原始数据**全部保留，不删**。但超过 `max_full_turns`（默认 20）的轮次：
- `user_message` / `ai_response` / `tool_results` 清空
- `summary` / `tags` / `cost` 等元数据保留
- 所以 `get_summaries()` 永远能拿到全部轮次的概要

### 实现演进

| 阶段 | 实现 | 存储 | 检索方式 |
|------|------|------|---------|
| **P0** | `SqliteConversationStore` | SQLite 单表 | turn_id/timestamp 排序 + LIKE 搜索 |
| **P1** | 升级 SQLite | SQLite + FTS5 索引 | 全文搜索 + tag 精确匹配 |
| **P2** | `PgConversationStore` | PostgreSQL + pgvector | 向量检索 + 混合搜索 |

---

## 任务系统

### 表 2：`tasks`

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_turn INTEGER NOT NULL,
    status_turn INTEGER,
    cancelled_reason TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP,
    user_feedback TEXT DEFAULT 'ok'            -- ok / good / not_work
);
CREATE INDEX idx_tasks_session ON tasks(session_id);
CREATE INDEX idx_tasks_status ON tasks(status);
```

### 表 3：`task_status_log`

```sql
CREATE TABLE task_status_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    reason TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
CREATE INDEX idx_task_log_task ON task_status_log(task_id);
CREATE INDEX idx_task_log_turn ON task_status_log(turn_id);
```

### 数据类

```python
@dataclass
class TaskItem:
    id: str
    session_id: str
    title: str
    status: str                  # pending / in_progress / blocked / cancelled / completed
    created_turn: int
    status_turn: int | None = None
    cancelled_reason: str | None = None
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    user_feedback: str = "ok"    # ok / good / not_work

@dataclass
class TaskStatusChange:
    task_id: str
    turn_id: int
    old_status: str | None
    new_status: str
    reason: str | None = None

@dataclass
class TaskStats:
    total: int
    pending: int
    in_progress: int
    blocked: int
    cancelled: int
    completed: int
```

### IConversationStore 扩展方法

```python
@abstractmethod
async def add_task(self, session_id: str, turn_id: int, title: str, sort_order: int = 0) -> str: ...
@abstractmethod
async def update_task_status(self, task_id: str, new_status: str, turn_id: int, reason: str = None): ...
@abstractmethod
async def get_session_tasks(self, session_id: str) -> list[TaskItem]: ...
@abstractmethod
async def get_tasks_at_turn(self, session_id: str, turn_id: int) -> list[TaskItem]: ...
@abstractmethod
async def search_tasks(self, session_id: str = None, query: str = "", status: str = None) -> list[TaskItem]: ...
@abstractmethod
async def get_task_stats(self, session_id: str = None) -> TaskStats: ...
@abstractmethod
async def get_task_history(self, task_id: str) -> list[TaskStatusChange]: ...
@abstractmethod
async def update_task_feedback(self, task_id: str, feedback: str): ...
@abstractmethod
async def get_feedback_stats(self, session_id: str = None) -> dict: ...
```

### 用户反馈闭环

三条反馈通道：

| 通道 | 触发 | 成本 |
|------|------|:----:|
| AI 自动推断 | 用户在对话中表达情绪 | **0 token**（嵌入同一轮回答） |
| AI 主动询问 | AI 不确定用户指哪个任务 → 调 `ask_choice` | ~50 token |
| 用户手动标注 | 在 Dashboard / TaskBoard 中点任务 → 选 ok/good/not_work | 无 |

```python
# system prompt 加一句：
"每次回答前判断用户是否在评价之前任务。
 确定 → 调 update_feedback(task_id, 'good'/'not_work')
 不确定 → 调 ask_choice 让用户选"
```

### AI 集成工具

```python
@tool(name="add_task")
def tool_add_task(title: str) -> str:
    store = Container.get("conversation_store")
    task_id = store.add_task(session_id, turn_id, title)
    return f"已添加任务: {title} (id={task_id})"

@tool(name="update_task")
def tool_update_task(task_id: str, status: str, reason: str = None) -> str:
    store = Container.get("conversation_store")
    store.update_task_status(task_id, status, turn_id, reason)
    return f"任务 {task_id} 状态已更新为 {status}"

@tool(name="update_feedback")
def update_feedback(task_id: str, feedback: str) -> str:
    """feedback: 'good' | 'not_work'（不调 = ok）"""
    store = Container.get("conversation_store")
    store.update_task_feedback(task_id, feedback)
    return f"任务 {task_id} 反馈已更新为 {feedback}"
```

---

## Checkpoint 系统

### 双层 Checkpoint

| 层级 | 触发时机 | 存储 | 用途 |
|:----:|---------|------|------|
| **turn:checkpoint** | 每完成一个工具调用 | SQLite（turns 表 partial 字段 + LangGraph checkpoints 表） | 崩溃恢复，重启继续 |
| **Git Checkpoint** | 每轮 AI 修改文件后 | `git commit` + `checkpoint_mappings` 表 | 文件级回溯 |

### turn:checkpoint（默认启用，零开销）

```python
@hook("tool:after", priority=50)
class TurnCheckpointHook:
    async def on_event(self, ctx: HookContext):
        store = Container.get("conversation_store")
        state = ctx.state
        await store.save_checkpoint(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
        )
```

每调完一个工具写一次，SQLite INSERT ~0.1ms。崩溃后检测到 `partial=True` 的轮次，弹提示"上一轮未正常结束，是否继续？"。

### Git Checkpoint（GitCheckpointManager）

```python
class GitCheckpointManager:
    async def init_repo(self, workspace: str): ...
    async def commit_turn(self, turn_id: int, summary: str) -> str:
        """做 git commit，返回 commit_hash"""
        repo = git.Repo(self.workspace)
        repo.index.add("*")
        commit = repo.index.commit(f"[turn_{turn_id}] {summary}")
        # 写入 checkpoint_mappings 表
        store = Container.get("conversation_store")
        store.save_checkpoint_map(turn_id, commit.hexsha, summary)
        return commit.hexsha
    async def restore(self, turn_id: int):
        """恢复到指定 turn 时的文件状态"""
        hash = store.get_checkpoint_map(turn_id)
        repo.git.checkout(hash)
```

### 回溯流程

```
用户: "回到改 auth 之前的状态"
  → 语义匹配到 turn_2
  → GitCheckpointManager.restore(turn_2)   ← 文件回退
  → get_tasks_at_turn(session_id, turn_2)  ← 任务状态回退
  → SSE 推送: {"type": "tasks_restored", "tasks": [...]}
```

---

## 用量追踪（Usage Tracker）

### 表 4：`turn_usage`

```sql
CREATE TABLE turn_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_id TEXT NOT NULL UNIQUE,
    trace_id TEXT,
    timestamp TEXT NOT NULL,
    model_name TEXT NOT NULL,
    call_count INTEGER DEFAULT 0,
    total_tokens_in INTEGER DEFAULT 0,
    total_tokens_out INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0.0,
    cache_hit_rate REAL DEFAULT 0.0,
    duration_ms INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed'
);
CREATE INDEX idx_turn_ts ON turn_usage(timestamp);
CREATE INDEX idx_turn_sid ON turn_usage(session_id);
```

### 表 5：`call_usage`

```sql
CREATE TABLE call_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id TEXT NOT NULL,
    call_index INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    tool_name TEXT,
    tool_args TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    cache_hit INTEGER DEFAULT 0,
    cost REAL DEFAULT 0.0,
    duration_ms INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success',
    FOREIGN KEY (turn_id) REFERENCES turn_usage(turn_id)
);
CREATE INDEX idx_call_turn ON call_usage(turn_id);
CREATE INDEX idx_call_ts ON call_usage(timestamp);
```

### 表 6：`model_pricing`

```sql
CREATE TABLE model_pricing (
    model_name TEXT NOT NULL,
    price_date TEXT NOT NULL,
    price_per_1k_in REAL NOT NULL,
    price_per_1k_out REAL NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (model_name, price_date)
);
```

### 接口

```python
class IUsageTracker(ABC):
    @abstractmethod
    async def record_turn(self, usage: TurnUsage): ...
    @abstractmethod
    async def get_turn_usage(self, turn_id: str) -> TurnUsage | None: ...
    @abstractmethod
    async def get_session_summary(self, session_id: str) -> dict: ...
    @abstractmethod
    async def query_by_time_range(self, start: str, end: str) -> list[TurnUsage]: ...
    @abstractmethod
    async def get_cache_stats(self, days: int = 7) -> dict: ...
```

### SqliteUsageTracker 实现

`SqliteUsageTracker` 与 `ConversationStore` 共用 `data/conversations.db`，各自管理自己的表。

完整实现见 `usage-tracking.md`（待合并），核心流程：

```
chat:before → 初始化 TurnUsage
tool:before → 创建 CallUsage
tool:after  → 补充 token/cost/cache
chat:after  → 聚合写入 turn_usage  + call_usage
```

### 数据滚动

启动时或每日首次对话检查，若数据量 > 100MB 或最早记录 > 90 天则弹窗让用户决定。**不做自动清理**。

---

## 代码知识图谱（IKnowledgeGraph，P1）

```python
class IKnowledgeGraph(ABC):
    async def index_project(project_root) -> None: ...
    async def search_entity(name, type) -> list[EntityLocation]: ...
    async def get_entity_relations(entity_name) -> list[Relation]: ...
    async def get_file_summary(file_path) -> FileSummary: ...
```

P0 用 NoOp 实现，P1 基于 tree-sitter AST 构建。**这也是长期记忆**——代码的关系网络持久化在 SQLite 中，跨会话可查。

---

## 数据关系总览

```
conversations.db
┌─────────────────────────────────────────────────────┐
│  turns (对话轮次)                                    │
│    turn_5 → turn_6 → turn_7                          │
│    每个 turn 关联:                                    │
│    ├── tasks (本轮创建/更新的任务)                     │
│    ├── turn_usage + call_usage (本轮用量)             │
│    ├── checkpoint_mappings (本轮 git commit hash)     │
│    └── user_feedback (本轮任务评价)                    │
│                                                       │
│  tasks ←→ task_status_log (任务变更历史)               │
│                                                       │
│  turn_usage ←→ call_usage (1:N，用量明细)              │
│                                                       │
│  model_pricing (每日价格快照，独立查询)                 │
└─────────────────────────────────────────────────────┘
```
