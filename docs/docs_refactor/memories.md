# 长期记忆系统（Memories）

> **来源**: `architecture-refactor.md` §3.7, §3.9
> **关联文档**: `short-term-memory.md`（上下文压缩）、`backend-modules.md`（DI 注册）、`api-reference.md`（查询端点）、`plan-task-system.md`（任务系统详细设计：AI 集成/SSE/前端组件/回溯）
> 所有持久化数据的统一描述：对话记录、任务、用量、checkpoint、反馈。

## 概述

长期记忆统一存储在 `conversations.db`（SQLite WAL 模式），共 9 张表：

| 表 | 用途 | 写入者 |
|:--:|------|:------:|
| `sessions` | 会话元数据（创建/最后活跃时间） | ConversationStore |
| `turns` | 对话轮次（含 partial 标记） | ConversationStore |
| `tasks` | 任务列表（含 user_feedback） | AI（tool_add_task） |
| `task_status_log` | 任务状态变更历史 | ConversationStore |
| `suggestions` | 对抗建议反馈记录 | ConversationStore |
| `turn_usage` | 每轮用量聚合 | SqliteUsageTracker |
| `call_usage` | 每次调用明细 | SqliteUsageTracker |
| `model_pricing` | 模型价格快照（每日） | PricingFetcher |
| `checkpoint_mappings` | turn_id → git commit_hash（回溯用） | GitCheckpointManager |

---

## 对话存储（ConversationStore）

> 替代原来散落的 IRepository / IHistoryStore / CheckpointStore。

### 表 1：`sessions`

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,                  -- session_001
    user_id TEXT NOT NULL,
    title TEXT,                            -- 会话标题（可自动生成）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP,
    turn_count INTEGER DEFAULT 0,
    workspace TEXT                         -- 关联的工作区路径
);
CREATE INDEX idx_sessions_user ON sessions(user_id);
```

### 表 2：`turns`

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

任务是 AI 拆解用户需求后生成的**结构化代办清单**。每个任务记录一件事（"重构路由"、"写测试"），有明确的状态流转和用户反馈。

### 核心哲学

- **没有 Plan 层级**——扁平的任务列表，一个方案天然由多个任务组成
- **每个任务都要记录**，不分大小。AI 拆解了子任务就写入数据库
- **通过 `turn_id` 串联**：任务创建、状态变更、checkpoint 都通过 `turn_id` 对齐
- **回溯时任务状态跟着回**：恢复某 turn 时，文件回退 + 任务状态也回到当时快照
- **无反馈 = 通过**：用户不评价 = `ok`，表扬 = `good`，抱怨 = `not_work`

### 任务状态

```
       ┌──────────┐
       │  pending  │ ← 创建后的初始状态
       └─────┬────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌────────┐ ┌──────────┐ ┌───────────┐
│blocked │ │in_progress│ │ cancelled │
└────┬───┘ └─────┬────┘ └───────────┘
     │          │
     │     ┌────┴─────┐
     │     ▼          ▼
     │  ┌────────┐ ┌──────────┐
     │  │completed│ │ cancelled│
     │  └────────┘ └──────────┘
     │
     └──────→ 恢复后可重新 in_progress
```

| 状态 | 含义 | 可转换到 |
|------|------|---------|
| `pending` | 已规划但未开始 | in_progress / cancelled |
| `in_progress` | 正在执行 | completed / blocked / cancelled |
| `blocked` | 中断/阻塞，等条件恢复 | in_progress / cancelled |
| `cancelled` | 决定不做 | — |
| `completed` | 已完成 | — |

### user_feedback 反馈体系

AI 任务执行完成后，用户通过三种渠道反馈：

| 渠道 | 触发条件 | 写入值 |
|------|---------|:------:|
| AI 自动推断 | 用户在对话中表达不满/表扬，AI 在下一轮回答中调 `update_feedback` | good / not_work |
| AI 主动询问 | AI 不确定用户指哪个任务 → 调 `ask_choice` 让用户选 | good / not_work |
| 用户手动打标 | 在 Dashboard/TaskBoard 中点任务打标 | ok / good / not_work |
| 默认 | 用户不反馈 | ok |

`user_feedback` 的用途：
- Dashboard 展示任务质量看板（good/ok/not_work 占比）
- AI 知道哪些任务用户不满意，下次对话中主动提出修复

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

## 对抗建议反馈（Suggestions）

### 表 4：`suggestions`

```sql
CREATE TABLE suggestions (
    id TEXT PRIMARY KEY,
    turn_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    text TEXT NOT NULL,
    rule_name TEXT,
    adopted INTEGER,                    -- 0=拒绝, 1=采纳, NULL=未反馈
    feedback_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_suggestions_turn ON suggestions(turn_id);
CREATE INDEX idx_suggestions_session ON suggestions(session_id);
```

用户采纳/拒绝 AI 的对抗建议时记录到 `adopted` 字段，用于后续分析建议质量。

```python
@dataclass
class SuggestionItem:
    id: str
    text: str
    rule_name: str
    adopted: bool | None       # None=未反馈, True=采纳, False=拒绝
    feedback_timestamp: datetime | None
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

### 表 7：`turn_usage`

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

### 表 8：`call_usage`

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

### 表 9：`model_pricing`

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

### 表 10：`code_graph`（P1 新增）

P1 阶段在 conversations.db 中新增代码关系网络表：

```sql
CREATE TABLE code_graph (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,         -- class / function / module
    file_path TEXT NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    relations TEXT,                    -- JSON 数组：关联实体列表
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_code_entity ON code_graph(entity_name);
CREATE INDEX idx_code_file ON code_graph(file_path);
```

```python
class IKnowledgeGraph(ABC):
    async def index_project(project_root) -> None: ...
    async def search_entity(name, type) -> list[EntityLocation]: ...
    async def get_entity_relations(entity_name) -> list[Relation]: ...
    async def get_file_summary(file_path) -> FileSummary: ...
```

P0 用 NoOp 实现，P1 基于 tree-sitter AST 构建。**这也是长期记忆**——代码的关系网络持久化在 SQLite 中，跨会话可查。

---

## LangMem 集成（P2 选项）

LangMem 不是 ConversationStore 的替代品，而是**额外的知识层**——AI 主动调用的工具。

### 和 ConversationStore 的对比

| 维度 | ConversationStore | LangMem |
|------|-----------------|---------|
| 存什么 | 对话记录 + 任务 + 用量 | 知识片段（"用户喜欢 FastAPI"） |
| 谁写 | 系统自动 | AI 主动调 `manage_memory()` |
| 谁读 | Pipeline 自动读 → 压缩 → 喂 LLM | AI 主动调 `search_memory()` |
| 写入频率 | 每轮 1 次 | AI 觉得有必要时才写 |
| 检索 | turn_id / timestamp / 全文 | 向量嵌入 + 语义搜索 |
| 数据量 | 全部对话（可能很大） | 精选知识点（轻量） |

### 集成方式

```python
from langmem import create_manage_memory_tool, create_search_memory_tool

memory_tools = [
    create_manage_memory_tool(namespace=("memories",), store=store_backend),
    create_search_memory_tool(namespace=("memories",), store=store_backend),
]
```

AI 在对话中自行决定何时调用：

```
用户: "还是按上次说的那个方案"
  AI 调 search_memory("上次说的方案") → "用户偏好 FastAPI + SQLite"

用户: "记住，我喜欢用 Pydantic"
  AI 调 manage_memory("用户喜欢用 Pydantic")
```

### 实现演进

| 阶段 | 方式 | 说明 |
|------|------|------|
| **P0（MVP）** | 不用 LangMem | ConversationStore 的 get_recent_turns 已经够用 |
| **P1（有用户）** | LangMem + SQLite | AI 能查/存知识点，后台自动提取 |
| **P2（向量库）** | LangMem + pgvector | 语义搜索精度提升 |

> LangMem 不是架构依赖。`IConversationStore.search()` 是对历史对话的搜索，LangMem 是对"提炼后的知识片段"的搜索，两者独立。

---

## 数据关系总览

```
conversations.db
┌─────────────────────────────────────────────────────┐
│  sessions (会话管理)                                  │
│    └── turns (对话轮次)                               │
│         turn_5 → turn_6 → turn_7                      │
│         每个 turn 关联:                                │
│          ├── tasks (本轮创建/更新的任务)               │
│          ├── suggestions (本轮对抗建议)               │
│          ├── turn_usage + call_usage (本轮用量)       │
│          ├── checkpoint_mappings (本轮 git hash)      │
│          └── user_feedback (本轮任务评价)              │
│                                                       │
│  tasks ←→ task_status_log (任务变更历史)               │
│  suggestions (对抗建议反馈记录)                        │
│                                                       │
│  turn_usage ←→ call_usage (1:N，用量明细)              │
│                                                       │
│  model_pricing (每日价格快照，独立查询)                 │
└─────────────────────────────────────────────────────┘
```
