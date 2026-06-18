# mem_convStore：对话存储总览

> **来源**: `architecture-refactor.md` §3.7, §3.9
> **关联文档**: `mem_convStore_tasks.md`（任务）、`mem_convStore_usage.md`（用量）、`mem_convStore_checkpoints.md`（Checkpoint）、`short-term-memory.md`（上下文压缩）

## 数据文件

`data/conversations.db`（SQLite WAL 模式）

## 所有表

| # | 表 | 用途 | 子文档 |
|:-:|:--:|------|:------:|
| 1 | `sessions` | 会话元数据 | — |
| 2 | `turns` | 对话轮次 | — |
| 3 | `tasks` | 任务列表 | `mem_convStore_tasks.md` |
| 4 | `task_status_log` | 任务状态变更历史 | `mem_convStore_tasks.md` |
| 5 | `suggestions` | 对抗建议反馈 | — |
| 6 | `turn_usage` | 每轮用量聚合 | `mem_convStore_usage.md` |
| 7 | `call_usage` | 每次调用明细 | `mem_convStore_usage.md` |
| 8 | `model_pricing` | 模型价格快照 | `mem_convStore_usage.md` |
| 9 | `checkpoint_mappings` | turn_id → git commit_hash | `mem_convStore_checkpoints.md` |
| 10 | `code_graph` | 代码关系网络（P1） | — |

## 数据关系

```
sessions ──┬── turns ──┬── tasks
            │            ├── task_status_log
            │            ├── suggestions
            │            ├── turn_usage ←→ call_usage
            │            ├── model_pricing
            │            └── checkpoint_mappings
            │
            └── code_graph（P1，独立）
```

## 接口

所有接口定义在 `domain/interfaces/`：

| 接口 | 文件 | 子文档 |
|:----:|:----:|:------:|
| `IConversationStore` | `iconversation_store.py` | —（总览，复用扩展方法见子文档） |
| `IUsageTracker` | `iusage_tracker.py` | `mem_convStore_usage.md` |

### 接口列表速览

**IConversationStore**：
- `save_turn()` / `get_recent_turns()` / `get_summaries()` / `search()`
- `list_sessions()` / `delete_session()`
- 任务方法 → `mem_convStore_tasks.md`
- checkpoint 方法 → `mem_convStore_checkpoints.md`

**IUsageTracker**：
- `record_turn()` / `get_turn_usage()` / `get_session_summary()`
- `query_by_time_range()` / `get_cache_stats()`
- 完整实现 → `mem_convStore_usage.md`

## 存储策略

原始数据全部保留不删。超过 `max_full_turns`（默认 20）的轮次清空 `user_message` / `ai_response` / `tool_results`，保留 `summary` 等元数据。

## 实现演进

| 阶段 | 实现 | 存储 | 检索方式 |
|------|------|------|---------|
| **P0** | `SqliteConversationStore` | SQLite 单表 | turn_id 排序 + LIKE |
| **P1** | SQLite + FTS5 | 全文搜索 | tag 精确匹配 |
| **P2** | `PgConversationStore` | PostgreSQL + pgvector | 混合搜索 |
