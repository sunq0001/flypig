# 用量追踪系统（IUsageTracker）

> **来源**: `architecture-refactor.md` §3.9（新增）
> **关联文档**: `backend-modules.md`（DI注册）、`api-reference.md`（查询端点）、`operations.md`（数据持久化策略）、`memories.md`（与 IConversationStore 的关系）

## 概述

独立于 `IConversationStore` 的用量追踪系统，采用 **时序数据模型**（每条记录按时间序列组织，查询以时间范围聚合为主）。

记录每个 Turn 内每次 Call 的模型、工具、Token、缓存、耗时、花费。

> **存储引擎选择**：数据模型是时序的（timestamp + 时间范围查询 + 聚合统计），但存储用 **SQLite + WAL 模式** 而非专用时序数据库（TimescaleDB/InfluxDB）。
> 原因：单用户本地场景下 SQLite 完全胜任（100 万条 call_usage 记录约 200MB，时间范围查询 < 10ms），避免引入额外依赖。

> **取代原 `ICostTracker`**。`IUsageTracker` 覆盖了 cost 追踪的全部能力（轮级 + call 级），`cost/` 模块不再存在，合并入 `usage/` 模块。

**核心哲学**："AI suggests, user decides" — 用量数据只记录不自动处理。数据滚动（超量提醒/归档/删除）仅通过弹窗让用户决定。

---

## 数据模型

### 表 1：`turn_usage` — 每轮一条

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | INTEGER PK | 自增主键 | 1 |
| `session_id` | TEXT | 会话 ID | `sess_abc123` |
| `turn_id` | TEXT | 轮次 ID | `turn_001` |
| `trace_id` | TEXT | 全链路追踪 ID | `trace_xyz` |
| `timestamp` | TEXT (ISO8601) | 时序索引，轮次开始时间 | `2026-06-11T22:30:00` |
| `model_name` | TEXT | 本轮使用的模型 | `deepseek-chat` |
| `call_count` | INTEGER | 本轮总调用次数 | 4 |
| `total_tokens_in` | INTEGER | 本轮输入总 token | 1500 |
| `total_tokens_out` | INTEGER | 本轮输出总 token | 800 |
| `reasoning_tokens` | INTEGER | 思考 token（R1 等推理模型专用） | 300 |
| `total_cost` | REAL | 本轮总花费（元） | 0.012 |
| `cache_hit_rate` | REAL | 缓存命中率 % | 45.5 |
| `duration_ms` | INTEGER | 本轮总耗时（ms） | 12300 |
| `status` | TEXT | `completed` / `interrupted` / `error` | `completed` |

### 表 2：`call_usage` — 每 Call 一条

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | INTEGER PK | 自增主键 | 5 |
| `turn_id` | TEXT | **外键 → turn_usage.turn_id** | `turn_001` |
| `call_index` | INTEGER | 第几个 call（从 1 开始） | 2 |
| `timestamp` | TEXT (ISO8601) | 该 call 发生时间 | `2026-06-11T22:30:05` |
| `tool_name` | TEXT | 调用的工具名（最后一答为 null） | `search_stock` |
| `tool_args` | TEXT | 工具参数字符串（截断 200 字） | `{"code":"600519"}` |
| `tokens_in` | INTEGER | 本 call 输入 token | 350 |
| `tokens_out` | INTEGER | 本 call 输出 token | 120 |
| `reasoning_tokens` | INTEGER | 本 call 思考 token | 80 |
| `cache_hit` | INTEGER | 是否命中缓存（0/1） | 1 |
| `cost` | REAL | 本 call 花费（元） | 0.003 |
| `duration_ms` | INTEGER | 本 call 耗时（ms） | 2100 |
| `status` | TEXT | `success` / `error` / `retry` | `success` |

### 表 3：`model_pricing` — 每日价格快照

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `model_name` | TEXT | 模型名（联合主键） | `deepseek-chat` |
| `price_date` | TEXT | 价格生效日期（联合主键） | `2026-06-11` |
| `price_per_1k_in` | REAL | 输入单价（元/1K tokens） | 0.0005 |
| `price_per_1k_out` | REAL | 输出单价（元/1K tokens） | 0.002 |
| `updated_at` | TEXT | 获取时间 | `2026-06-11T08:00:00` |

### 示意图：一个 Turn 的实际存储

```
turn_usage 表写入 1 行:
  session_id=turn_001 | model=deepseek-chat | call_count=4 | total_tokens=2300 | cost=0.012 | cache_hit_rate=45.5

call_usage 表写入 4 行:
  call_index=1 | tool_name=search_stock  | tokens=500+200 | reasoning=0  | cache_hit=0 | cost=0.004 | status=success
  call_index=2 | tool_name=get_price     | tokens=400+150 | reasoning=0  | cache_hit=0 | cost=0.003 | status=success
  call_index=3 | tool_name=format_result | tokens=350+130 | reasoning=0  | cache_hit=1 | cost=0.002 | status=success
  call_index=4 | tool_name=null          | tokens=250+320 | reasoning=80 | cache_hit=1 | cost=0.003 | status=success
```

---

## 接口定义

```python
@dataclass
class CallUsage:
    call_index: int
    timestamp: str
    tool_name: str | None          # null 表示最终回答
    tool_args: str | None          # 截断 200 字
    tokens_in: int
    tokens_out: int
    reasoning_tokens: int = 0
    cache_hit: bool = False
    price_in_effect: float = 0.0   # 本 call 实际使用的输入单价
    price_out_effect: float = 0.0  # 本 call 实际使用的输出单价
    cost: float = 0.0
    duration_ms: int = 0
    status: str = "success"        # success / error / retry

@dataclass
class TurnUsage:
    session_id: str
    turn_id: str
    trace_id: str
    timestamp: str
    model_name: str
    call_count: int
    total_tokens_in: int
    total_tokens_out: int
    reasoning_tokens: int = 0
    total_cost: float = 0.0
    cache_hit_rate: float = 0.0   # 百分比
    duration_ms: int = 0
    status: str = "completed"
    calls: list[CallUsage] = field(default_factory=list)

class IUsageTracker(ABC):
    """用量追踪接口 — 独立于 IConversationStore"""

    @abstractmethod
    async def record_turn(self, usage: TurnUsage): ...

    @abstractmethod
    async def get_turn_usage(self, turn_id: str) -> TurnUsage | None: ...

    @abstractmethod
    async def get_session_summary(self, session_id: str) -> dict:
        """当前会话汇总: total_tokens, total_cost, avg_cache_hit_rate"""

    @abstractmethod
    async def query_by_time_range(self, start: str, end: str) -> list[TurnUsage]:
        """时间范围查询（用于跨会话统计）"""

    @abstractmethod
    async def get_cache_stats(self, days: int = 7) -> dict:
        """缓存命中率统计"""
```

---

## 价格获取

### 时机

- **当天首次 SSE 连接**时触发一次
- **跨午夜处理**：每日 00:00（UTC+8）自动**获取一次最新价格**
- 若价格未变 → 不发任何通知
- 若价格变更 → 推 SSE 事件通知用户，后续 call 使用新价格

### 实现

```python
class PricingFetcher:
    _cache: dict[str, dict] = {}    # model_name -> {price_in, price_out, date}

    async def ensure_pricing(self, model_name: str) -> dict:
        """确保当日价格已获取，返回 {price_in, price_out}"""
        today = date.today().isoformat()
        cached = self._cache.get(model_name)
        if cached and cached["date"] == today:
            return cached  # 内存缓存命中

        # 从 model_pricing 表查
        row = await db.query(
            "SELECT * FROM model_pricing WHERE model_name=? AND price_date=?",
            model_name, today
        )
        if row:
            self._cache[model_name] = dict(row)
            return self._cache[model_name]

        # 在线获取官方最新价格
        prices = await self._fetch_from_official(model_name)
        if prices:
            await db.execute(
                "INSERT INTO model_pricing VALUES (?, ?, ?, ?, ?, datetime('now'))",
                model_name, today, prices["in"], prices["out"]
            )
            self._cache[model_name] = {**prices, "date": today}
            return self._cache[model_name]

        # 获取失败 → 沿用最后已知价格
        last = await db.query(
            "SELECT * FROM model_pricing WHERE model_name=? ORDER BY price_date DESC LIMIT 1",
            model_name
        )
        return dict(last) if last else {"price_per_1k_in": 0, "price_per_1k_out": 0}

    async def _fetch_from_official(self, model_name: str) -> dict | None:
        """从 DeepSeek 官方定价页面获取最新价格"""
        # TODO: 实现具体抓取逻辑
        pass
```

### 定价源

- **DeepSeek**: 官方定价页面 `https://api-docs.deepseek.com/zh-cn/quick_start/pricing`
- **Qwen**: 官方定价页面（备用）
- 后续模型按需添加

---

## 集成方式

### 通过 EventSubscriptions 自动记录

```python
# infrastructure/usage/usage_handler.py
class UsageTrackerHook:
    def __init__(self, tracker: IUsageTracker):
        self.tracker = tracker
        self._current_turn: TurnUsage | None = None
        self._pricing_fetcher = PricingFetcher()

    @hook("chat:before")
    async def on_chat_start(self, ctx: HookContext):
        """本轮开始时初始化 TurnUsage"""
        pricing = await self._pricing_fetcher.ensure_pricing(ctx.data.get("model", "deepseek-chat"))
        self._current_turn = TurnUsage(
            session_id=ctx.data["session_id"],
            turn_id=ctx.data["turn_id"],
            trace_id=ctx.data["trace_id"],
            timestamp=datetime.utcnow().isoformat(),
            model_name=ctx.data.get("model", "deepseek-chat"),
            call_count=0,
            total_tokens_in=0,
            total_tokens_out=0,
            total_cost=0.0,
            cache_hit_rate=0.0,
            duration_ms=0,
        )

    @hook("tool:before")
    async def on_tool_call(self, ctx: HookContext):
        """工具调用开始时记录 CallUsage"""
        pricing = await self._pricing_fetcher.ensure_pricing(self._current_turn.model_name)
        call = CallUsage(
            call_index=len(self._current_turn.calls) + 1,
            timestamp=datetime.utcnow().isoformat(),
            tool_name=ctx.data.get("tool_name"),
            tool_args=str(ctx.data.get("tool_args", ""))[:200],
            price_in_effect=pricing.get("price_per_1k_in", 0),
            price_out_effect=pricing.get("price_per_1k_out", 0),
            duration_ms=0,
            status="success",
        )
        self._current_turn.calls.append(call)

    @hook("tool:after")
    async def on_tool_result(self, ctx: HookContext):
        """工具调用完成后补充 token/cost"""
        call = self._current_turn.calls[-1]
        call.tokens_in = ctx.data.get("tokens_in", 0)
        call.tokens_out = ctx.data.get("tokens_out", 0)
        call.reasoning_tokens = ctx.data.get("reasoning_tokens", 0)
        call.cache_hit = ctx.data.get("cache_hit", False)
        call.duration_ms = ctx.data.get("duration_ms", 0)
        call.status = ctx.data.get("status", "success")
        # 计算 cost: tokens * price / 1000
        call.cost = (call.tokens_in * call.price_in_effect + call.tokens_out * call.price_out_effect) / 1000

    @hook("chat:after")
    async def on_chat_end(self, ctx: HookContext):
        """本轮结束时聚合计算并存储"""
        turn = self._current_turn
        if not turn:
            return
        turn.total_tokens_in = sum(c.tokens_in for c in turn.calls)
        turn.total_tokens_out = sum(c.tokens_out for c in turn.calls)
        turn.reasoning_tokens = sum(c.reasoning_tokens for c in turn.calls)
        turn.total_cost = sum(c.cost for c in turn.calls)
        turn.call_count = len(turn.calls)
        cached = sum(1 for c in turn.calls if c.cache_hit)
        turn.cache_hit_rate = (cached / turn.call_count * 100) if turn.call_count > 0 else 0
        turn.duration_ms = ctx.data.get("duration_ms", 0)
        turn.status = ctx.data.get("status", "completed")

        await self.tracker.record_turn(turn)
        self._current_turn = None
```

### DI 注册

```python
# 在 Container.configure() 中添加:
usage_tracker = SqliteUsageTracker("data/conversations.db")  # 实现 IUsageTracker，共享统一库
usage_hook = UsageTrackerHook(usage_tracker)
cls.register("usage_tracker", usage_tracker, singleton=True)
# hook_service 自动注册所有 hook 函数
```

---

## 查询 API

```python
# 新增路由文件: flypig/backend/routes/usage.py

# GET /api/usage/turn/<turn_id>       — 本轮用量明细
# GET /api/usage/session/<session_id> — 当前会话汇总
# GET /api/usage/range?start=&end=    — 时间范围统计
# GET /api/usage/cache-stats?days=7   — 缓存命中率统计
```

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/usage/turn/<turn_id>` | GET | 返回 `TurnUsage`（含 calls[] 明细） |
| `/api/usage/session/<session_id>` | GET | 返回 `{total_turns, total_tokens, total_cost, avg_cache_hit}` |
| `/api/usage/range?start=&end=` | GET | 返回 `{turns: [...], summary: {total_cost, avg_cache_hit}}` |
| `/api/usage/cache-stats?days=7` | GET | 返回 `{daily_hit_rate: [{date, rate}], avg_7d}` |

### SSE 事件扩展

在 `response_end` 事件中嵌入本轮用量摘要：

```python
{"type": "response_end", "usage": {
    "prompt_tokens": 2300,
    "completion_tokens": 800,
    "reasoning_tokens": 80,
    "cache_hit_rate": 45.5,
    "cost": 0.012,
    "duration_ms": 12300
}}
```

---

## 前端展示（当前）

每个 Turn 结束后，在对话消息底部显示一轮用量摘要行：

```
🔄 call: 4 次 | 📥 in: 1.5K | 📤 out: 0.8K | 💭 think: 80 | 💰 ¥0.012 | ⚡ 12.3s
```

**独立用量界面（未来）**：侧边栏或独立页面，展示趋势图表（日/周/月 Token 消耗、费用趋势、缓存命中率）。数据已经有了，UI 以后做。

---

## 数据滚动策略

### 触发条件

启动时或每日首次对话时检查一次，若任一条件触发则弹窗提醒：

```
条件 A: 数据量 > 100MB（估算约 50 万条 call_usage 记录）
条件 B: 最近记录 > 90 天
```

### 弹窗内容

```
{{usage_tracker}} 检测到用量数据已积累 {{size_human}}，超过 {{threshold}}。
建议归档或删除旧数据以释放空间。
- [归档到文件] -> 导出为 JSON/CSV，保存到用户指定位置
- [删除旧数据] -> 仅保留最近 90 天
- [稍后提醒] -> 下次启动再问
```

用户选择后执行对应操作。**不做自动清理**。

### 每轮用量推送

每次 `response_end` 事件中推送本轮用量给前端→客户端 IndexedDB 实时写入→用户即时看到。IndexedDB 在每次 SSE 连接建立时将缓冲数据同步到服务端。

> **P0 简化**：仅服务端 SQLite `data/conversations.db`（用量表合并），不做 IndexedDB 缓冲和同步。P1 再补客户端侧。

---

## 与 IConversationStore 的关系

| 维度 | ConversationStore | UsageTracker |
|------|-----------------|--------------|
| key | `session_id + turn_id` | `timestamp + trace_id` |
| 查询模式 | 按 session 取最近 N 轮 | 按时间范围聚合统计 |
| 数据量 | 每轮 1 条（大，含完整内容） | 每轮 N+1 条（小，仅有统计量） |
| 生命周期 | 永久保留 | 可滚动/聚合（90 天后用户决定） |
| 是否可选 | 必需 | 可选（没它也能跑） |
| 存储 | `data/conversations.db`（统一库，用量表合并） | `data/conversations.db` |

---

## 时序数据模型：一条记录长什么样子

以 `call_usage` 表为例，用户一次提问产生 N 条记录（N = call 数），每条是一个"时序数据点"：

```json
{
  "timestamp": "2026-06-11T22:30:05",
  "turn_id": "turn_001",
  "call_index": 2,
  "tool_name": "get_price",
  "tokens_in": 400,
  "tokens_out": 150,
  "reasoning_tokens": 0,
  "cache_hit": 0,
  "cost": 0.003,
  "duration_ms": 2100,
  "status": "success"
}
```

`turn_usage` 1 条聚合 + `call_usage` N 条明细 = 完整用量追踪。

## SQLite 存储实现

### 数据流

```
EventSubscriptions 事件流                          SSE 响应
━━━━━━━━━━━━━━━━━━━━━━                      ━━━━━━━━━━━━━━━━
chat:before → 初始化 TurnUsage              response_end
tool:before → 创建 CallUsage              → { usage: {...} }
tool:after  → 补充 token/cost/cache       → 前端渲染摘要行
chat:after  → 聚合写入 conversations.db 的 turn_usages/call_usages 表 → (无 SSE 事件)

                    ↓
          ┌─────────────────┐
          │  SqliteUsageTracker  │
          │  conversations.db (turn_usages 表) │
          │  WAL 模式        │
          └────────┬────────┘
                   ↓
          ┌─────────────────┐
          │  查询 API 读取   │
          │  /api/usage/*   │
          └─────────────────┘
```

### SqliteUsageTracker 实现

```python
class SqliteUsageTracker(IUsageTracker):
    """IUsageTracker 的 SQLite 实现。数据文件: data/conversations.db（共享）"""

    def __init__(self, db_path: str = "data/conversations.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """建表（首次启动时执行）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # 高并发写入优化
            conn.execute("""
                CREATE TABLE IF NOT EXISTS turn_usage (
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
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_turn_ts ON turn_usage(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_turn_sid ON turn_usage(session_id)")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS call_usage (
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
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_call_turn ON call_usage(turn_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_call_ts ON call_usage(timestamp)")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_pricing (
                    model_name TEXT NOT NULL,
                    price_date TEXT NOT NULL,
                    price_per_1k_in REAL NOT NULL,
                    price_per_1k_out REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (model_name, price_date)
                )
            """)

    async def record_turn(self, usage: TurnUsage):
        """写入一轮用量（1 条 turn + N 条 call）"""
        with sqlite3.connect(self.db_path) as conn:
            # 写入 turn 聚合
            conn.execute("""
                INSERT OR REPLACE INTO turn_usage
                (session_id, turn_id, trace_id, timestamp, model_name,
                 call_count, total_tokens_in, total_tokens_out, reasoning_tokens,
                 total_cost, cache_hit_rate, duration_ms, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                usage.session_id, usage.turn_id, usage.trace_id, usage.timestamp,
                usage.model_name, usage.call_count,
                usage.total_tokens_in, usage.total_tokens_out, usage.reasoning_tokens,
                usage.total_cost, usage.cache_hit_rate, usage.duration_ms, usage.status,
            ))

            # 批量写入 call 明细
            conn.executemany("""
                INSERT INTO call_usage
                (turn_id, call_index, timestamp, tool_name, tool_args,
                 tokens_in, tokens_out, reasoning_tokens, cache_hit, cost, duration_ms, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(
                usage.turn_id, c.call_index, c.timestamp, c.tool_name, c.tool_args,
                c.tokens_in, c.tokens_out, c.reasoning_tokens, int(c.cache_hit),
                c.cost, c.duration_ms, c.status,
            ) for c in usage.calls])

    async def get_turn_usage(self, turn_id: str) -> TurnUsage | None:
        """读取一轮明细（含 calls[]）"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM turn_usage WHERE turn_id = ?", (turn_id,)
            ).fetchone()
            if not row:
                return None
            calls = [
                CallUsage(**dict(c)) for c in conn.execute(
                    "SELECT * FROM call_usage WHERE turn_id = ? ORDER BY call_index",
                    (turn_id,)
                ).fetchall()
            ]
            return TurnUsage(**dict(row), calls=calls)

    async def get_session_summary(self, session_id: str) -> dict:
        """会话汇总：总 turn 数、总 token、总 cost、平均缓存命中率"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT COUNT(*) as total_turns,
                       SUM(total_tokens_in) as total_tokens_in,
                       SUM(total_tokens_out) as total_tokens_out,
                       SUM(total_cost) as total_cost,
                       AVG(cache_hit_rate) as avg_cache_hit
                FROM turn_usage WHERE session_id = ?
            """, (session_id,)).fetchone()
            return dict(row) if row else {}

    async def query_by_time_range(self, start: str, end: str) -> list[TurnUsage]:
        """时间范围查询"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM turn_usage WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
                (start, end)
            ).fetchall()
            return [TurnUsage(**dict(r)) for r in rows]

    async def get_cache_stats(self, days: int = 7) -> dict:
        """每日缓存命中率统计"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT date(timestamp) as day,
                       SUM(cache_hit) * 1.0 / COUNT(*) * 100 as hit_rate
                FROM call_usage
                WHERE timestamp >= date('now', '-' || ? || ' days')
                GROUP BY day ORDER BY day
            """, (days,)).fetchall()
            return {"daily": [dict(r) for r in rows]}

    async def get_storage_stats(self) -> dict:
        """获取数据文件大小和使用情况（用于数据滚动提醒）"""
        db_size = os.path.getsize(self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            total_turns = conn.execute("SELECT COUNT(*) FROM turn_usage").fetchone()[0]
            total_calls = conn.execute("SELECT COUNT(*) FROM call_usage").fetchone()[0]
            oldest = conn.execute("SELECT MIN(timestamp) FROM turn_usage").fetchone()[0]
            newest = conn.execute("SELECT MAX(timestamp) FROM turn_usage").fetchone()[0]
        return {
            "db_path": self.db_path,
            "size_bytes": db_size,
            "size_human": f"{db_size / 1024 / 1024:.1f} MB",
            "total_turns": total_turns,
            "total_calls": total_calls,
            "oldest_timestamp": oldest,
            "newest_timestamp": newest,
        }
```

### 数据滚动检查

在 `ChatService` 启动时或每日首次对话时调用：

```python
async def check_usage_storage():
    tracker = Container.get("usage_tracker")
    stats = await tracker.get_storage_stats()

    threshold_mb = 100        # 超过 100MB 提醒
    threshold_days = 90       # 超过 90 天提醒

    if stats["size_bytes"] > threshold_mb * 1024 * 1024 or \
       days_since(stats["oldest_timestamp"]) > threshold_days:
        # 推弹窗给前端，让用户决定
        yield {
            "type": "notification",
            "title": "用量数据存储提醒",
            "content": (
                f"用量数据已积累 {stats['size_human']}，"
                f"共 {stats['total_turns']} 轮 / {stats['total_calls']} 条调用。"
                "建议归档或删除旧数据。"
            ),
            "actions": [
                {"label": "归档到文件", "value": "archive"},
                {"label": "删除旧数据（保留 90 天）", "value": "delete"},
                {"label": "稍后提醒", "value": "later"},
            ],
        }
```

> **关联文档**: `backend-modules.md`（DI注册）、`api-reference.md`（查询端点）、`operations.md`（数据持久化+备份）、`plan-task-system.md`（IConversationStore vs UsageTracker 对比）、`resilience.md`（Schema 迁移 + 日志系统）
