---
name: plan-task-system
overview: 设计 Plan/Task 任务系统，作为 IConversationStore 的扩展，覆盖任务状态管理、回溯、前端展示方案
design:
  architecture:
    framework: vue
  styleKeywords:
    - Professional
    - Clean
    - Task Tracking
  fontSystem:
    fontFamily: PingFang SC
    heading:
      size: 14px
      weight: 600
    subheading:
      size: 13px
      weight: 500
    body:
      size: 12px
      weight: 400
  colorSystem:
    primary:
      - "#409EFF"
      - "#2196F3"
      - "#1976D2"
    background:
      - "#F5F7FA"
      - "#FFFFFF"
      - "#F0F9EB"
    text:
      - "#303133"
      - "#606266"
      - "#909399"
    functional:
      - "#4CAF50"
      - "#FF9800"
      - "#F44336"
      - "#2196F3"
      - "#9E9E9E"
todos:
  - id: create-plan-task-system-doc
    content: 创建 plan-task-system.md 主设计文档，含数据模型、接口扩展、回溯机制、AI 集成方式、SSE 事件、前端设计
    status: completed
  - id: update-extensions-conversationstore
    content: 更新 extensions.md：IConversationStore 接口新增 task CRUD 抽象方法
    status: completed
    dependencies:
      - create-plan-task-system-doc
  - id: update-frontend-arch-taskboard
    content: 更新 frontend-arch.md：重写 TaskBoard 章节，新增 TaskCard 和 TaskHistoryView 组件设计
    status: completed
    dependencies:
      - create-plan-task-system-doc
  - id: update-api-reference-tasks
    content: 更新 api-reference.md：新增 6 个 task 端点和 task_update SSE 事件格式
    status: completed
    dependencies:
      - create-plan-task-system-doc
  - id: update-backend-langgraph-folder-archdiagram
    content: 批量更新 backend-modules.md、langgraph-graph.md、folder-tree.md、architecture-diagram.md：加入任务相关模块和路由
    status: completed
    dependencies:
      - create-plan-task-system-doc
  - id: update-data-flow-crossref
    content: 更新 data-flow.md（task 数据流）、usage-tracking.md（交叉引用）、architecture-refactor.md（交叉引用链接）
    status: completed
    dependencies:
      - create-plan-task-system-doc
---

## 任务系统（Plan/Task System）

在 IConversationStore 中集成任务系统，所有任务存入 conversations.db，通过 turn_id 关联 checkpoint 结果。

### 核心功能

1. **任务状态全集**：pending（待办）、in_progress（进行中）、blocked（已中断/阻塞）、cancelled（已取消，显示删除线）、completed（已完成）
2. **状态流转**：pending → in_progress → completed；pending/in_progress 均可 → blocked 或 cancelled
3. **存入 IConversationStore**：conversations.db 新增 tasks 表 + task_status_log 表，通过 turn_id 关联 checkpoint
4. **当前会话任务卡片（TaskCard）**：对话流中内嵌展示当前会话的任务进度，每个任务一行状态图标+标题+状态标签，已取消显示删除线，底部进度条
5. **侧边栏任务看板（TaskBoard）**：当前会话全部任务列表，支持搜索和状态筛选
6. **历史任务检索（TaskHistoryView）**：跨会话搜索历史任务，展示所属会话和创建 turn，点击跳转
7. **所有任务都记录**：不分大小，AI 拆解的任何子任务都创建 Task 记录
8. **SSE 事件**：task_update 事件实时推送任务状态变更

## 技术方案

### 数据模型（conversations.db 新增两张表）

```sql
-- 任务表：每个任务一条
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    tags TEXT,                            -- JSON array
    parent_task TEXT,                     -- 父任务 ID（支持子任务）
    created_turn INTEGER NOT NULL,        -- 哪个 turn 创建
    status_turn INTEGER,                  -- 哪个 turn 更新了当前状态（关联 checkpoint）
    cancelled_reason TEXT,                -- 取消原因
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX idx_tasks_session ON tasks(session_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- 任务状态变更日志：回溯时重建当时快照
CREATE TABLE task_status_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    reason TEXT,                          -- 变更原因
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
CREATE INDEX idx_task_log_task ON task_status_log(task_id);
CREATE INDEX idx_task_log_turn ON task_status_log(turn_id);
```

### IConversationStore 接口扩展

在 `extensions.md` 的 IConversationStore 接口中新增以下抽象方法：

```python
class IConversationStore(ABC):
    # ... 现有方法 ...

    @abstractmethod
    async def add_task(self, session_id: str, turn_id: int, title: str,
                       tags: list[str] = None, parent_task: str = None) -> str:
        """添加任务，返回 task_id"""

    @abstractmethod
    async def update_task_status(self, task_id: str, new_status: str,
                                  turn_id: int, reason: str = None):
        """更新任务状态 + 自动写入 task_status_log"""

    @abstractmethod
    async def get_tasks(self, session_id: str, status: str = None) -> list[dict]:
        """获取会话全部任务，可选按状态筛选"""

    @abstractmethod
    async def get_task_at_turn(self, session_id: str, turn_id: int) -> list[dict]:
        """回溯到某个 turn 时的任务状态快照"""

    @abstractmethod
    async def search_tasks(self, query: str, status: str = None,
                            session_id: str = None) -> list[dict]:
        """跨会话搜索任务"""

    @abstractmethod
    async def get_task_stats(self, session_id: str = None) -> dict:
        """任务统计：各状态数量和总进度"""
```

### 回溯机制

`get_task_at_turn` 的工作原理：对每个任务，查 `task_status_log` 找到给定 turn_id 之前的最新一条状态变更记录。如果某个任务在 turn_id 之后才创建，则在快照中不可见。这确保了回溯时任务状态与 checkpoint 的文件快照一致。

例如：用户回溯到 turn_3，此时 task_002（在 turn_5 创建）不应该出现，task_001（在 turn_2 创建，turn_3 完成）应该显示为 completed——与 checkpoint 的文件状态匹配。

### API 端点

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/api/tasks?session_id=&status=` | GET | 获取会话任务列表 |
| `/api/tasks/at-turn/<turn_id>?session_id=` | GET | 回溯某 turn 时的任务快照 |
| `/api/tasks/search?q=&status=&session_id=` | GET | 跨会话搜索任务 |
| `/api/tasks/stats?session_id=` | GET | 任务统计（Dashboard 用） |
| `/api/tasks` | POST | 添加任务 |
| `/api/tasks/<id>` | PATCH | 更新任务状态 |


### SSE 事件

```
{"type": "task_update", "data": {
    "task_id": "task_003",
    "title": "创建 users 表",
    "status": "completed",
    "turn_id": 5
}}
```

### AI 集成

通过两个工具让 AI 操作任务：

```python
def tool_add_task(title: str, tags: list[str] = None, parent_task: str = None) -> str:
    """添加任务到会话任务列表"""
    store = Container.get("conversation_store")
    session_id = ...   # 从 AgentState 取
    turn_id = ...      # 从 AgentState 取
    return store.add_task(session_id, turn_id, title, tags, parent_task)

def tool_update_task(task_id: str, status: str, reason: str = None) -> str:
    """更新任务状态"""
    store = Container.get("conversation_store")
    turn_id = ...      # 从 AgentState 取
    store.update_task_status(task_id, status, turn_id, reason)
```

工具文件：`infrastructure/tools/tool_task_manager.py`（复用现有文件名，但改为调用 IConversationStore）

### AgentState 扩展

```python
class AgentState(TypedDict):
    # ... 现有字段 ...
    active_tasks: list[dict]   # 当前活跃任务列表（对话流中的 TaskCard 用）
```

AgentState 的 `active_tasks` 字段在 chat_node 启动时从 store 加载，状态变更后实时更新，用于对话流中的 TaskCard 渲染。

### 前端组件

- **TaskCard.vue（chat/）**：对话流中内嵌任务卡片，实时显示当前会话任务进度
- 每行：状态图标 + 标题 + 状态标签
- 已取消：`<s>`删除线`</s>` + 灰色
- 底部：`进度: 2/5 完成, 1 取消`
- **TaskBoard.vue（sidebar/）**：侧边栏任务看板
- 搜索框 + 状态筛选 tabs
- 支持展开子任务
- **TaskHistoryView.vue（sidebar/ 或独立视图）**：跨会话历史任务搜索
- 按关键词/状态/时间范围搜索
- 每行显示：标题 + 状态 + 所属会话 + turn_id
- 点击跳转到对应会话

### 颜色系统（任务状态）

| 状态 | 颜色 | 图标 |
| --- | --- | --- |
| pending | #9E9E9E 灰色 | ○ 空心圆 |
| in_progress | #2196F3 蓝色 | 🔄 旋转 |
| blocked | #FF9800 橙色 | ⚡ 闪电 |
| cancelled | #9E9E9E 灰色 + 删除线 | ~~text~~ |
| completed | #4CAF50 绿色 | ✅ 勾选 |


### 涉及文档

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `docs/docs_refactor/plan-task-system.md` | 新增 | 任务系统主设计文档 |
| `docs/docs_refactor/extensions.md` | 修改 | IConversationStore 接口加 task CRUD 方法 |
| `docs/docs_refactor/frontend-arch.md` | 修改 | TaskBoard 重写 + TaskCard/TaskHistoryView |
| `docs/docs_refactor/api-reference.md` | 修改 | 新增 task 端点和 task_update SSE |
| `docs/docs_refactor/backend-modules.md` | 修改 | tasks.py 路由 + tool_task_manager |
| `docs/docs_refactor/langgraph-graph.md` | 修改 | AgentState 加 active_tasks |
| `docs/docs_refactor/architecture-diagram.md` | 修改 | 任务相关框 |
| `docs/docs_refactor/folder-tree.md` | 修改 | 新增 task 相关文件 |
| `docs/docs_refactor/data-flow.md` | 修改 | task 数据流 |
| `docs/docs_refactor/usage-tracking.md` | 修改 | 交叉引用 |
| `docs/architecture-refactor.md` | 修改 | 交叉引用链接到 plan-task-system.md |


## 设计风格

继续沿用现有前端架构（Vue 3 + Element Plus），不做大的 UI 风格改动。任务卡片（TaskCard）、任务看板（TaskBoard）、历史任务检索（TaskHistoryView）三个组件沿用现有组件的视觉风格。

### TaskCard（对话流内嵌）

内嵌在 MessageItem 之间出现，浅色背景卡片，左侧竖条颜色条标识状态。每个任务一行，紧凑布局，右侧状态标签。底部进度条采用 Element Plus el-progress。

- 已取消任务：文字灰色 + 删除线
- 已完成任务：文字绿色 + 勾选图标
- 正在进行的任务：文字蓝色 + 旋转动画

### TaskBoard（侧边栏）

侧边栏面板（与 FileTree 同级），顶部搜索框，中间状态筛选 tabs，下方任务列表。每个任务显示：状态图标 + 标题 + 创建 turn 信息。

- 支持搜索筛选：搜索框用 el-input + el-icon
- 状态筛选：el-radio-group 或 el-tabs
- 任务列表：自定义列表，每项可点击展开详情
- 已取消任务：灰色删除线

### TaskHistoryView（独立视图/侧边栏）

跨会话搜索界面，搜索框 + 高级筛选项（时间范围、状态、会话）。结果列表包含任务标题、状态、所属会话名、创建 turn、完成 turn、点击跳转链接。

- 搜索框：el-input + 搜索按钮
- 高级筛选项：el-select（状态）+ el-date-picker（时间范围）
- 结果列表：el-table 风格自定义列表
- 每行有「跳转到会话」链接