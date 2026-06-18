# 长期记忆系统（Memories）

> **来源**: `architecture-refactor.md` §3.7, §3.9
> **关联文档**: `mem_convStore_tasks.md`（任务详细设计）、`mem_convStore_usage.md`（用量追踪详细设计）、`mem_convStore_checkpoints.md`（Checkpoint 系统）、`short-term-memory.md`（上下文压缩）、`backend-modules.md`（DI 注册）、`api-reference.md`（查询端点）
> 所有持久化数据的统一描述。每个子项有独立文档包含前端/后端/SSE 完整设计。

## 概述

长期记忆统一存储在 `conversations.db`（SQLite WAL 模式），共 9 张表：

| # | 表 | 用途 | 写入者 | 详细文档 |
|:-:|:--:|------|:------:|:--------:|
| 1 | `sessions` | 会话元数据 | ConversationStore | — |
| 2 | `turns` | 对话轮次（含 partial） | ConversationStore | — |
| 3 | `tasks` | 任务列表（含 user_feedback） | AI（tool_add_task） | `mem_convStore_tasks.md` |
| 4 | `task_status_log` | 任务状态变更历史 | ConversationStore | `mem_convStore_tasks.md` |
| 5 | `suggestions` | 对抗建议反馈 | ConversationStore | — |
| 6 | `turn_usage` | 每轮用量聚合 | SqliteUsageTracker | `mem_convStore_usage.md` |
| 7 | `call_usage` | 每次调用明细 | SqliteUsageTracker | `mem_convStore_usage.md` |
| 8 | `model_pricing` | 模型价格快照 | PricingFetcher | `mem_convStore_usage.md` |
| 9 | `checkpoint_mappings` | turn_id → git commit_hash | GitCheckpointManager | `mem_convStore_checkpoints.md` |

---

## 对话存储接口（IConversationStore）

```python
# domain/interfaces/iconversation_store.py

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

### 存储策略

原始数据全部保留不删。超过 `max_full_turns`（默认 20）的轮次清空 `user_message` / `ai_response` / `tool_results`，保留 `summary` / `tags` / `cost` 等元数据。

## 用量追踪接口（IUsageTracker）

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

> 完整实现 + 数据流 + API 端点 → `mem_convStore_usage.md`

## 代码知识图谱（IKnowledgeGraph，P1）

```python
class IKnowledgeGraph(ABC):
    async def index_project(project_root) -> None: ...
    async def search_entity(name, type) -> list[EntityLocation]: ...
    async def get_entity_relations(entity_name) -> list[Relation]: ...
    async def get_file_summary(file_path) -> FileSummary: ...
```

P0 NoOp，P1 基于 tree-sitter AST 构建。

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

> LangMem 不是架构依赖。P0 不启用，P1 有用户时再用。
