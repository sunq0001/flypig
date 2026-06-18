# 任务管理系统（Plan/Task System）

> **来源**: 新增模块，作为 `IConversationStore` 的扩展
> **关联文档**: `extensions.md`（IConversationStore 接口）、`frontend-arch.md`（前端组件）、`api-reference.md`（查询端点）、`langgraph-graph.md`（AgentState）、`usage-tracking.md`（与用量追踪的数据层次差异）

## 概述

任务系统是 IConversationStore 的内置扩展，**不做独立接口**。所有任务 CRUD 直接通过 IConversationStore 的 `conversations.db` 完成，与对话消息、checkpoint 共享同一数据源。

### 核心哲学

- **没有 Plan 层级**——扁平的任务列表。一个"方案"天然由多个任务组成
- **每个任务都要记录**，不分大小。只要 AI 拆解了子任务，就写入数据库
- **通过 `turn_id` 串联**：任务创建、状态变更、checkpoint 都通过 `turn_id` 对齐
- **回溯时任务状态跟着回**：恢复某个 turn 时，不仅文件回到 checkpoint，任务状态也回到当时快照
- **无反馈 = 通过**：用户不评价 = ok，表扬 = good，抱怨 = not_work

---

## 任务状态

```
       ┌──────────┐
       │  pending  │ ← 创建后的初始状态
       └─────┬────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌────────┐ ┌──────────┐ ┌───────────┐
│blocked │ │in_progress│ │ cancelled │ ← ~~删除线~~
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

| 状态 | 含义 | 前端展示 | 可转换到 |
|------|------|---------|---------|
| `pending` | 已规划但未开始 | ⬜ 灰底圆点 | in_progress / cancelled |
| `in_progress` | 正在执行 | 🔄 蓝色旋转图标 | completed / blocked / cancelled |
| `blocked` | 中断/阻塞，等条件恢复 | ⚡ 黄色警告 | in_progress(恢复) / cancelled |
| `cancelled` | 决定不做 | 删除线 ~~文字~~ | — |
| `completed` | 已完成 | ✅ 绿色对勾 | — |

---

## 数据模型

### 表 1：`tasks`（在 `conversations.db` 中）

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,                     -- "task_001"
    session_id TEXT NOT NULL,
    title TEXT NOT NULL,                      -- 任务描述
    status TEXT NOT NULL DEFAULT 'pending',   -- pending / in_progress / blocked / cancelled / completed
    created_turn INTEGER NOT NULL,            -- 哪个 turn 创建了这个任务
    status_turn INTEGER,                      -- 哪个 turn 最后一次更新状态（关联 checkpoint）
    cancelled_reason TEXT,                    -- 取消原因（回溯时看到"用户决定不做了"）
    sort_order INTEGER DEFAULT 0,             -- 排序
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP,
    user_feedback TEXT DEFAULT 'ok'            -- ok / good / not_work（★ 用户反馈）
);
CREATE INDEX idx_tasks_session ON tasks(session_id);
CREATE INDEX idx_tasks_status ON tasks(status);
```

`cancelled_reason` 示例：
- `"用户决定先不实现"`
- `"需求变更，不再需要"`
- `"替代方案：使用第三方 SDK"`

### 表 2：`task_status_log`（状态变更日志，回溯快照用）

```sql
CREATE TABLE task_status_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,                -- 哪个 turn 变更的
    old_status TEXT,                          -- 之前状态（NULL 表示创建）
    new_status TEXT NOT NULL,                 -- 新状态
    reason TEXT,                              -- 变更原因
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
CREATE INDEX idx_task_log_task ON task_status_log(task_id);
CREATE INDEX idx_task_log_turn ON task_status_log(turn_id);
```

### 数据模型可视化

```
conversations.db
┌──────────────────────────────────────────────────────────┐
│                                                           │
│  turns (已有):                                            │
│    turn_1: "帮我实现登录模块…" → AI 回复 → checkpoint#abc   │
│    turn_2: AI 创建任务列表 → checkpoint#def               │
│    turn_3: AI 完成"创建 users 表" → checkpoint#ghi        │
│    ...                                                    │
│                                                           │
│  tasks (新增):                                            │
│    task_001: "创建 users 表"   created_turn=2  → ✅ done │
│    task_002: "实现 login API"  created_turn=2  → 🔄 wip  │
│    task_003: "实现注册页面"     created_turn=2  → ❌ cancelled │
│                                                           │
│  task_status_log (新增):                                  │
│    task_001: pending → in_progress (turn=2)               │
│    task_001: in_progress → completed  (turn=3)            │
│    task_003: pending → cancelled    (turn=5, "用户决定…") │
└──────────────────────────────────────────────────────────┘
```

---

## IConversationStore 接口扩展

```python
# domain/models/task.py (新增)
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
    user_feedback: str = "ok"                  # ok / good / not_work（★ 用户反馈）

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

```python
# domain/interfaces/iconversation_store.py
# 新增以下抽象方法

class IConversationStore(ABC):
    # ======== 已有方法（save_turn, get_recent_turns, search 等）========

    # ======== Task CRUD ========

    @abstractmethod
    async def add_task(self, session_id: str, turn_id: int, title: str,
                       sort_order: int = 0) -> str:
        """添加任务到会话，返回 task_id"""

    @abstractmethod
    async def update_task_status(self, task_id: str, new_status: str,
                                  turn_id: int, reason: str = None):
        """
        更新任务状态。
        - 写入 task_status_log 一行（回溯时重建快照用）
        - 如果 new_status 是 completed，设置 completed_at
        - 如果 new_status 是 cancelled 且 reason 不为空，记录取消原因
        """

    @abstractmethod
    async def get_session_tasks(self, session_id: str) -> list[TaskItem]:
        """获取会话全部任务，按 sort_order 排序"""

    @abstractmethod
    async def get_tasks_at_turn(self, session_id: str, turn_id: int) -> list[TaskItem]:
        """
        恢复到指定 turn 时的任务状态快照。
        原理：通过 task_status_log 回溯每个任务在 turn_id 时的最新状态。
        用户回溯到 turn_5 时，不仅 checkpoint 回退，任务状态也回到当时。
        """

    @abstractmethod
    async def search_tasks(self, session_id: str = None,
                           query: str = "", status: str = None) -> list[TaskItem]:
        """跨会话搜索任务，按标题匹配"""

    @abstractmethod
    async def get_task_stats(self, session_id: str = None) -> TaskStats:
        """任务统计：总数/各状态数量（Dashboard 用）"""

    @abstractmethod
    async def get_task_history(self, task_id: str) -> list[TaskStatusChange]:
        """单个任务的完整状态变更历史（用于查看任务生命线）"""
```

### SqliteConversationStore 实现要点

```python
# orchestration/conversation_store.py
# 在 _init_db() 中新增建表

class SqliteConversationStore(IConversationStore):
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            # ... 原有建表 ...

            # 新增：tasks 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
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
                    completed_at TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")

            # 新增：task_status_log 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_status_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    turn_id INTEGER NOT NULL,
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    reason TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_log_task ON task_status_log(task_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_log_turn ON task_status_log(turn_id)")
```

### `get_tasks_at_turn` 回溯实现

```python
async def get_tasks_at_turn(self, session_id: str, turn_id: int) -> list[TaskItem]:
    """
    回溯到指定 turn 时的任务快照。
    算法：
      1. 获取该 session 所有任务
      2. 对每个任务，查 task_status_log 中 turn_id ≤ 参数 turn_id 的最新一条
      3. 返回每个任务在那个时刻的状态
    """
    with sqlite3.connect(self.db_path) as conn:
        rows = conn.execute("""
            SELECT t.*, sl.new_status as snapshot_status,
                   sl.reason as snapshot_reason
            FROM tasks t
            LEFT JOIN task_status_log sl ON sl.id = (
                SELECT id FROM task_status_log
                WHERE task_id = t.id AND turn_id <= ?
                ORDER BY turn_id DESC, id DESC LIMIT 1
            )
            WHERE t.session_id = ?
            ORDER BY t.sort_order
        """, (turn_id, session_id)).fetchall()
        return [self._row_to_task(r) for r in rows]
```

---

## AI 集成方式

### 通过工具调用（推荐）

两个简单工具，AI 在对话中自然调用：

```python
# infrastructure/tools/system/tool_task_manager.py

def tool_add_task(title: str) -> str:
    """
    添加任务到当前会话的任务列表。
    AI 在拆解用户需求、规划步骤时调用。
    """
    store = Container.get("conversation_store")
    session_id = Container.get("session_service").current_session_id
    turn_id = Container.get("session_service").current_turn_id
    task_id = store.add_task(session_id, turn_id, title)
    return f"已添加任务: {title} (id={task_id})"

def tool_update_task(task_id: str, status: str, reason: str = None) -> str:
    """
    更新任务状态。
    status: pending / in_progress / blocked / cancelled / completed
    reason: 状态变更原因（cancel 时必填）
    """
    store = Container.get("conversation_store")
    turn_id = Container.get("session_service").current_turn_id
    store.update_task_status(task_id, status, turn_id, reason)
    return f"任务 {task_id} 状态已更新为 {status}"
```

### 对话中的自然交互

```
用户: "帮我重构一下 auth 模块，需要改路由、加中间件、写测试"
  AI → tool_add_task("重构 auth 路由")
     → tool_add_task("新增 JWT 中间件")
     → tool_add_task("编写 auth 测试")
  → SSE 推送 task_update 事件 → TaskListCard 实时更新

AI 开始做第一项:
  → tool_update_task("task_001", "in_progress")
  → 执行重构

用户: "JWT 先不做了，用自带的 session 就行"
  → tool_update_task("task_002", "cancelled", reason="改用 session 方案")
  → 前端 task_002 显示 ~~新增 JWT 中间件~~

AI 完成第一项:
  → tool_update_task("task_001", "completed")
  → checkpoint 写入
```

### 自动创建策略（可选增强）

AI 在对话中自然输出结构化列表时，系统可自动识别并创建任务：

```python
# 在 chat_node 中增加自动任务检测
# 检测 AI 回复中是否包含类似 "1) ... 2) ... 3) ..." 的结构
# 若检测到，自动追加 tool_add_task 调用
```

**P0 阶段**只用手动 `tool_add_task` / `tool_update_task`，P1 再加自动检测。

---

## 用户反馈闭环

### 三条反馈通道（零交互成本）

```
AI 完成任务的下一轮回答：
  ┌─ system prompt 加一句指令 ──────────────────────┐
  │ "每次回答前判断用户是否在评价之前任务。            │
  │  确定 → 调 update_feedback(task_id, 'good'/'not_work')  │
  │  不确定 → 调 ask_choice 让用户选                 │
  │  无反馈 → 默认 ok（不动）"                        │
  └─────────────────────────────────────────────────┘
           │
           ▼
   同一轮回复中完成，token 零增长
```

| 通道 | 触发 | 成本 |
|------|------|:----:|
| AI 自动推断 | 用户在对话中表达情绪（"不错"/"又没改对"） | **0 token**（嵌入同一轮回答） |
| AI 主动询问 | AI 不确定用户指哪个任务 → 调 `ask_choice` 出选择题 | ~50 token |
| 用户手动标注 | 在 Dashboard / TaskBoard 中点任务 → 选 ok/good/not_work | 无 |

### 工具扩展

```python
# infrastructure/tools/system/tool_task_manager.py 追加

def update_feedback(task_id: str, feedback: str) -> str:
    """
    更新用户对任务的反馈。
    feedback: 'good' | 'not_work'
    不调 = ok（默认）
    AI 在回答中评估用户情绪后自动调用，不单独调模型。
    """
    store = Container.get("conversation_store")
    store.update_task_feedback(task_id, feedback)
    return f"任务 {task_id} 反馈已更新为 {feedback}"
```

### IConversationStore 接口扩展

```python
# domain/interfaces/iconversation_store.py（新增）

@abstractmethod
async def update_task_feedback(self, task_id: str, feedback: str):
    """更新用户反馈：ok / good / not_work"""

@abstractmethod
async def get_feedback_stats(self, session_id: str = None) -> dict:
    """反馈统计（Dashboard 用）：good/ok/not_work 各多少"""
```

### SSE 事件

```python
# feedback_update 事件（AI 调 update_feedback 时推送）
{"type": "task_feedback", "task_id": "task_001", "feedback": "good"}
```

### Dashboard 手动打标

Dashboard.vue / TaskBoard.vue 中每个任务右侧加反馈按钮组：

```
┌─ 任务看板 ─────────────────────────────────┐
│  🔄 重构 auth 路由           [进行中] [👍] │
│  ⬜ 性能优化                 [待办]   [👎] │
│  ✅ 创建 users 表            [已完成] 👍   │  ← 已标记 good
│  ✅ 修复数据库连接           [已完成] 👎   │  ← 已标记 not_work
│  ⬜ 测试覆盖率提升           [待办]         │  ← 默认 ok（不显示）
└────────────────────────────────────────────┘
```

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/tasks?session_id=xxx` | GET | 当前会话全部任务（按 sort_order） |
| `/api/tasks/at-turn/<turn_id>?session_id=xxx` | GET | 回溯某 turn 时的任务状态快照 |
| `/api/tasks/search?q=xxx&status=xxx` | GET | 跨会话搜索任务 |
| `/api/tasks/stats?session_id=xxx` | GET | 任务统计（Dashboard 用） |
| `/api/tasks/<id>/history` | GET | 单个任务状态变更历史 |
| `/api/tasks` | POST | AI 调 tool_add_task 写入 |
| `/api/tasks/<id>` | PATCH | AI 调 tool_update_task 更新状态 |

### SSE 事件

```python
# task_update 事件（AI 调 tool_add_task / tool_update_task 时推送）

# 添加任务
{"type": "task_update", "action": "add", "task": {
    "id": "task_001",
    "title": "重构 auth 路由",
    "status": "pending",
    "created_turn": 5
}}

# 更新状态
{"type": "task_update", "action": "update", "task": {
    "id": "task_001",
    "status": "in_progress",
    "turn_id": 6
}}

# 取消（带原因）
{"type": "task_update", "action": "update", "task": {
    "id": "task_003",
    "status": "cancelled",
    "turn_id": 8,
    "reason": "改用 session 方案"
}}
```

---

## 前端组件

### 1. TaskListCard.vue — 当前方案任务状态卡片（对话流中）

展示在当前对话消息流中，紧跟在 AI 拆解任务的消息下方：

```
┌─ 当前方案: 重构 auth 模块 ──────────────────┐
│  🔄 重构 auth 路由           [进行中]        │
│  ⬜ 新增 JWT 中间件          [待办]          │
│  ~~编写 auth 测试~~          [已取消]        │
│  ⬜ 性能优化                 [待办]          │
│                                             │
│  进度: ■■□□□  1/4 完成 · 1 取消              │
└─────────────────────────────────────────────┘
```

- 高亮当前进行中的任务（蓝色边框）
- 已完成的加 ✅ 和绿色文字
- 已取消的用 `<s>` 删除线
- 已中断的加 ⚡ 黄色标识
- 底部进度条 + 统计

### 2. TaskBoard.vue — 完整任务看板（侧边栏）

支持搜索、筛选、历史查看：

```
┌─ 任务看板 ─────────────────────────────────┐
│  🔍 搜索任务...        [全部▾]              │
│                                            │
│  📅 今天                                    │
│  🔄 重构 auth 路由           [进行中]       │
│  ⬜ 性能优化                 [待办]         │
│                                            │
│  📅 昨天                                    │
│  ✅ 创建 users 表            [已完成]       │
│  ⚡ 修复数据库连接           [已中断]       │
│  ~~实现注册页面~~              [已取消]     │
│                                            │
│  共 5 个任务 · 1 进行中 · 2 完成 · 1 中断 · 1 取消 │
└────────────────────────────────────────────┘
```

- 按时间分组（今天/昨天/更早）
- 状态筛选 tabs（全部/待办/进行/中断/已完成/已取消）
- 每个任务点击 → TaskHistoryDialog

### 3. TaskHistoryDialog.vue — 单个任务生命线（弹窗）

点击任务查看完整状态变更历史：

```
┌─ 任务: 重构 auth 路由 ──────────────────────┐
│                                            │
│  🕐 turn_5  创建        → pending          │
│  🕐 turn_5  开始做      → in_progress      │
│  🕐 turn_6  完成        → completed        │
│                                            │
│  关联 checkpoint: turn_6                    │
│  (可点击跳转到该 turn 的回复)                 │
└────────────────────────────────────────────┘
```

### 4. Dashboard 集成

在 Dashboard.vue 首页显示任务概览卡片：

```
┌─ 任务概览 ────────────────────┐
│  2 个活跃会话 · 5 个未完成任务 │
│                               │
│  📂 stock-app:    3 待办      │
│  📂 my-project:   2 待办      │
│                               │
│  [查看全部任务 →]              │
└──────────────────────────────┘
```

---

## 回溯集成

用户回溯到某个 turn 时，完整的流程：

```
用户: "回到改 auth 之前的状态"
  → 语义匹配到 turn_2
  → GitCheckpointManager.restore(turn_2)  ← 文件回到 checkpoint
  → get_tasks_at_turn(session_id, turn_2) ← 任务状态快照
  → SSE 推送:
      {"type": "tasks_restored", "tasks": [...], "turn_id": 2}
  → frontend:
      - 文件树刷新
      - TaskBoard 显示 turn_2 时的任务快照
      - 顶部提示栏: "已回到 turn_2 的状态"
```

**效果**：不只是文件回到过去，整个任务上下文也回到那个时刻。

---

## 与 IUsageTracker 的关系

| 维度 | Tasks（本文） | UsageTracker |
|------|-------------|--------------|
| 存什么 | 任务标题、状态、变更历史 | token 数、耗时、花费 |
| 关联 turn_id | 创建/变更都关联，可回溯快照 | 按轮汇总统计 |
| 查询模式 | 按 session 取任务列表 | 按时间范围聚合 |
| 数据量 | 每轮 ≤10 条 | 每轮 N+1 条（大） |
| 生命周期 | 不删除，永久保留 | 用户决定归档/删除 |
| 存储 | `conversations.db`（统一库） | `conversations.db`（统一库） |
| 可选性 | 必需（核心 UX） | 可选 |

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `domain/models/task.py` | 新增 | TaskItem / TaskStatusChange / TaskStats 数据类 |
| `domain/interfaces/iconversation_store.py` | 修改 | 新增 7 个 task CRUD + update_task_feedback 抽象方法 |
| `orchestration/conversation_store.py` | 修改 | SqliteConversationStore 实现 task 方法 |
| `infrastructure/tools/system/tool_task_manager.py` | 新增 | tool_add_task / tool_update_task / update_feedback 工具 |
| `backend/routes/tasks.py` | 新增 | 7 个 REST 端点 |
| `frontend/static_vite/src/components/chat/TaskListCard.vue` | 新增 | 对话流中的任务状态卡片 |
| `frontend/static_vite/src/components/sidebar/TaskBoard.vue` | 新增 | 侧边栏任务看板 |
| `frontend/static_vite/src/components/common/TaskHistoryDialog.vue` | 新增 | 任务状态变更历史弹窗 |
| `frontend/static_vite/src/components/sidebar/Dashboard.vue` | 修改 | 首页添加任务概览卡片 + 任务反馈打标 |
| SSE 事件 | 新增 | `task_update`（add/update）+ `task_feedback`（反馈）+ `tasks_restored`（回溯） |
