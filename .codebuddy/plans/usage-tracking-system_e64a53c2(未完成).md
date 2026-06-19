---
name: usage-tracking-system
overview: 设计并文档化用量追踪系统（IUsageTracker）：独立于 IConversationStore 的时序型接口，支持服务端 SQLite 持久化 + 客户端 IndexedDB 缓冲，覆盖模型/工具/Token/缓存/成本的逐轮逐调用记录与查询 API。
todos:
  - id: create-usage-tracking-doc
    content: 新增 usage-tracking.md 主设计文档，含 IUsageTracker 接口、数据模型、HookService 集成方案、存储策略、Query API 设计
    status: pending
  - id: update-backend-modules
    content: 更新 backend-modules.md：DI 容器注册、应用层服务表加 UsageTracker
    status: pending
    dependencies:
      - create-usage-tracking-doc
  - id: update-api-reference
    content: 更新 api-reference.md：新增 4 个用量查询端点和 SSE 事件
    status: pending
    dependencies:
      - create-usage-tracking-doc
  - id: update-operations-extensions-crossref
    content: 更新 operations.md（新 db 文件持久化）、extensions.md（关联引用）、architecture-refactor.md（交叉引用）
    status: pending
    dependencies:
      - create-usage-tracking-doc
---

## 用量追踪系统 (UsageTracker)

在现有 IConversationStore 之外，新增独立的用量追踪模块，记录每轮对话中每次 LLM 调用和工具调用的消耗明细。

### 核心功能

- **调用级记录**：每次 LLM/tool call 记录 model、token (prompt/completion)、缓存命中率、花费、耗时
- **轮次汇总**：每轮自动聚合 total_calls、total_tokens、total_cost、cache_hit_rate
- **跨会话查询**：按时间范围、模型、会话等维度聚合统计
- **前端用量面板**：展示当前会话的实时 token 消耗和花费趋势
- **通过 session_id + turn_id 关联 IConversationStore**，在对话详情旁展示用量信息

## 技术方案

### 核心概念

`IConversationStore` (对话文本) 和 `IUsageTracker` (用量数据) 是**两个独立接口，通过 session_id + turn_id 外键关联**。

```
IConversationStore           IUsageTracker (新增)
    └── TurnRecord                ├── TurnUsage  (1条/轮, 汇总)
        └── cost: float           └── CallUsage  (N条/轮, 明细)
```

`TurnRecord.cost` 保留作为从 `CallUsage` 聚合而来的金额摘要，无需改动已有接口。

### 数据模型

```python
# domain/interfaces/iusage_tracker.py

@dataclass
class TurnUsage:
    """轮次级用量——每轮一条汇总"""
    session_id: str
    turn_id: int
    model: str                    # 本轮用的模型
    started_at: datetime
    ended_at: datetime | None
    total_calls: int              # 本轮 LLM/tool call 总数
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cached_tokens: int
    cache_hit_rate: float         # 缓存 token / 总 token
    total_cost: float

@dataclass
class CallUsage:
    """调用级明细——每次 LLM call 或 tool call 一条"""
    session_id: str
    turn_id: int
    call_index: int               # 本轮内序号
    trace_id: str                 # session_id_turn_id (关联日志)
    span_id: str                  # trace_id_call_index (关联日志)
    call_type: str                # "llm" | "tool"
    tool_name: str | None         # 工具名（tool call 时）
    is_cached: bool               # 是否命中缓存
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    duration_ms: int
    timestamp: datetime
```

### 接口定义

```python
class IUsageTracker(ABC):
    @abstractmethod
    async def record_call(self, usage: CallUsage): ...
        """记录一次调用（LLM 或 tool），由 HookService 自动触发"""

    @abstractmethod
    async def finalize_turn(self, session_id: str, turn_id: int): ...
        """轮次结束时，聚合 CallUsage 生成 TurnUsage"""

    @abstractmethod
    async def get_turn_usage(self, session_id: str, turn_id: int) -> TurnUsage | None: ...

    @abstractmethod
    async def get_session_usage(self, session_id: str) -> list[TurnUsage]: ...
        """获取整个会话的轮次汇总列表"""

    @abstractmethod
    async def get_calls(self, session_id: str, turn_id: int) -> list[CallUsage]: ...
        """获取指定轮次的调用明细"""

    @abstractmethod
    async def get_total_cost(self, session_id: str | None = None) -> float: ...

    @abstractmethod
    async def get_model_usage_stats(self, days: int = 30) -> list[dict]: ...
        """按模型聚合统计（用于用量仪表盘）"""

    @abstractmethod
    async def delete_session_data(self, session_id: str): ...
```

### 集成方式（HookService 自动记录）

```python
# chat_node 中自动触发
hook_service.emit("llm:before", {"session_id": s, "turn_id": t, "model": m, "timestamp": now})
hook_service.emit("llm:after",  {"session_id": s, "turn_id": t, "call_index": i, "prompt_tokens": p, "completion_tokens": c, "cached_tokens": ch, "cost": cost, "duration_ms": d})

# execute_node 中自动触发
hook_service.emit("tool:before", {"session_id": s, "turn_id": t, "tool_name": n})
hook_service.emit("tool:after",  {"session_id": s, "turn_id": t, "call_index": i, "duration_ms": d})

# chat_node 结束
usage_tracker.finalize_turn(session_id, turn_id)
```

### 存储方案

- **服务端 SQLite（主存储）**：`data/usage.db` 独立文件，WAL 模式。两张表 `turn_usage` + `call_usage`
- **客户端 IndexedDB（P1 可选）**：SSE 事件流中实时写入本地，提供离线缓冲和即时展示

### Query API（新增端点）

```
GET  /api/usage/session/{session_id}                       -> 会话用量汇总列表
GET  /api/usage/session/{session_id}/{turn_id}              -> 单轮 TurnUsage + CallUsage 明细
GET  /api/usage/stats?days=30&model=deepseek-chat           -> 按模型/时段聚合统计
GET  /api/usage/cost/total                                  -> 总花费
```

### DI Container 注册

```python
class Container:
    @classmethod
    def configure(cls, env="web"):
        # ... 已有代码 ...
        usage_tracker = SqliteUsageTracker("data/usage.db")
        cls.register("usage_tracker", usage_tracker, singleton=True)
```

### 前端用量面板（新增组件）

- `UsagePanel.vue`：展示当前会话的 real-time tokens 和花费
- `UsageBar.vue`：每条消息旁的微型 token/cost 标签
- 数据来源：SSE 事件流中实时记录，或定期从 `/api/usage/session/{id}` 拉取

### 涉及文档

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `docs/docs_refactor/usage-tracking.md` | 新增 | 主设计文档，含接口/数据模型/集成方式 |
| `docs/docs_refactor/backend-modules.md` | 修改 | DI 容器注册、应用层服务表加 UsageTracker |
| `docs/docs_refactor/api-reference.md` | 修改 | 新增 4 个用量查询端点 |
| `docs/docs_refactor/operations.md` | 修改 | 新增 `data/usage.db` 数据持久化 |
| `docs/docs_refactor/extensions.md` | 修改 | 文档开头加 usage-tracking.md 关联引用 |
| `docs/docs_refactor/architecture-refactor.md` | 修改 | 交叉引用链接 |