# API 参考

> **来源**: `architecture-refactor.md` §3.1, §3.8.2-3.8.5, §8.3
> **关联文档**: `frontend-arch.md`（前端消费）、`data-flow.md`（数据流）、`usage-tracking.md`（用量查询端点）、`plan-task-system.md`（任务端点）
> 新增端点或改 SSE 事件格式时，需同步检查 frontend-arch.md 和 data-flow.md。

## REST 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | SSE 流式对话 |
| `/api/config` | GET/PUT | 配置查询/修改 |
| `/api/files` | GET | 文件列表 |
| `/api/file` | GET | 文件内容 |
| `/api/tree` | GET | 文件树 |
| `/api/sessions` | GET | 历史会话列表 |
| `/api/sessions/<session_id>/restore` | GET | 恢复断点：返回全部消息 + AgentState（turn_id、mode、persona），前端 `useChat({ initialMessages })` 恢复对话 |
| `/api/health` | GET | 健康检查 |
| `/api/upload` | POST | 文件上传 + 解压 |
| `/api/rollback/<turn_id>` | POST | 回滚到指定 turn_id 的文件状态 |
| `/api/rollback/search` | POST | 自然语言搜索回滚点，返回匹配列表或 choice_card |
| `/api/history/search` | GET | 历史搜索 |
| `/api/agent/status` | GET | Agent 运行状态（空闲/忙碌/当前任务/成本统计） |
| `/api/agent/stop` | POST | 强制停止当前运行中的 Agent |
| `/api/tasks?session_id=` | GET | 当前会话任务列表（按 sort_order 排序） |
| `/api/tasks/at-turn/<turn_id>?session_id=` | GET | 回溯某 turn 时的任务状态快照 |
| `/api/tasks/search?q=&status=` | GET | 跨会话搜索任务 |
| `/api/tasks/stats?session_id=` | GET | 任务统计（Dashboard 用） |
| `/api/tasks/<id>/history` | GET | 单个任务状态变更历史 |
| `/api/tasks` | POST | 添加任务（AI 调用 tool_add_task） |
| `/api/tasks/<id>` | PATCH | 更新任务状态（AI 调用 tool_update_task） |
| `/api/usage/turn/<turn_id>` | GET | 本轮用量明细（含 calls[]） |
| `/api/usage/session/<session_id>` | GET | 当前会话汇总（total_tokens, total_cost, avg_cache_hit） |
| `/api/usage/range?start=&end=` | GET | 时间范围统计 |
| `/api/usage/cache-stats?days=7` | GET | 缓存命中率趋势 |
| `/api/feedback/suggestion` | POST | 用户提交建议反馈（✅/❌），记录 `suggestion_id` + `adopted` |

## SSE 事件格式（/api/chat）

| 事件类型 | 说明 | 触发时机 |
|----------|------|---------|
| `token` | 逐 token 文本 | LLM 流式输出 |
| `reasoning` | LLM 推理过程片段 | LLM 思考中间步骤（防止用户以为卡死） |
| `task_update` | 任务状态变更 | AI 调 tool_add_task / tool_update_task 时推送。action: add(新任务) / update(状态变更) |
| `choice` | 选择题卡片 | Explore 模式 |
| `approval` | 审批卡片 | Plan 模式确认/修改 |
| `change_plan` | 变更计划（改前预览，逐项批准） | AI 输出修改方案后、执行前 |
| `change_review` | 变更后审查（对比计划与实际） | Execute 执行后 |
| `suggestion` | 对抗建议卡片（含 `suggestion_id`） | 变更评分后 |
| `response_end` | 结束 + usage | 本轮结束 |


```python
# token 事件（逐 token 推流）
{"type": "token", "content": "每个"}

# task_update 事件（AI 创建/更新任务时推送）
{"type": "task_update", "action": "add", "task": {
    "id": "task_001",
    "title": "重构 auth 路由",
    "status": "pending",
    "created_turn": 5
}}
{"type": "task_update", "action": "update", "task": {
    "id": "task_001",
    "status": "completed",
    "turn_id": 7
}}
{"type": "task_update", "action": "update", "task": {
    "id": "task_002",
    "status": "cancelled",
    "turn_id": 8,
    "reason": "改用 session 方案"
}}

# tasks_restored 事件（回溯到某 turn 后推送任务快照）
{"type": "tasks_restored", "tasks": [
    {"id": "task_001", "title": "重构 auth 路由", "status": "pending", "created_turn": 5},
    {"id": "task_002", "title": "新增 JWT 中间件", "status": "in_progress", "created_turn": 5}
], "turn_id": 5}

# response_end 事件（结束 + usage）
{"type": "response_end", "usage": {
    "prompt_tokens": 2300,
    "completion_tokens": 800,
    "reasoning_tokens": 80,
    "cache_hit_rate": 45.5,
    "cost": 0.012,
    "duration_ms": 12300
}}

# choice 事件（Explore 模式）
{
    "type": "choice",
    "id": "db_type",
    "question": "需要什么类型的数据库？",
    "options": [
        {"label": "SQLite", "desc": "轻量本地", "value": "sqlite"},
        {"label": "PostgreSQL", "desc": "生产可靠", "value": "postgres"},
        {"label": "MySQL", "desc": "生态成熟", "value": "mysql"},
    ],
    "multi_select": false,
}

# approval 事件（Plan 模式，伪装成 tool_call 让 useChat 原生处理）
{
    "type": "tool_call",
    "name": "_ask_approval",
    "arguments": {
        "category": "file",
        "tool": "delete_file",
        "params": {"path": "main.py"},
        "diff": "+ import os\n- old_code()",
        "prompt": "确认修改 main.py？"
    }
}
```

## Git 回滚（两套 Git 隔离）

### 整体架构

工作区维护两套独立的 Git 上下文：

| Git | 目录 | 用途 | 谁控制 |
|-----|------|------|--------|
| **用户 Git** | `项目根/.git` | 用户自己的版本管理 | 用户自己 |
| **Agent Git** | `项目根/.flypig_checkpoints` | AI 每次文件变更后自动 checkpoint | AI（隐藏目录） |

两套 Git 互不干扰。Agent 的 checkpoint 操作不会影响用户的 `git status`。

### 何时创建 checkpoint

| 触发时机 | 说明 |
|---------|------|
| `write_file`/`edit_file` 工具调用成功后 | 即使只是新建文件 |
| bash 命令改变文件系统后（`git add`、`rm`、`mv` 等，不含查询） | 检测文件变更 |
| 用户通过变更审查卡片点击"批准"后 | 批准的内容涉及文件修改 |
| 用户手动点击 Dashboard"保存里程碑" | 可选 |

每次 checkpoint 前执行 `git add -A`（只针对工作区，不影响用户 Git），然后 commit。

### Commit Message 格式

```
[turn_<turn_id>] <自动生成的简短摘要>

<可选：触发来源，如"批准变更" / "手动保存">
```

示例：

```
[turn_3] 修改 auth.py，新增 login_user 函数，测试通过
批准变更
```

- `turn_id` 来自 ChatService 维护的计数器
- 摘要由 SummaryGenerator 生成（≤ 50 字符）
- 正文可附加测试结果、变更评分等元数据

### CheckpointStore（SQLite）

```sql
CREATE TABLE checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    commit_hash TEXT NOT NULL,
    summary TEXT NOT NULL,
    source TEXT DEFAULT 'auto',         -- 'auto' | 'approval' | 'manual'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,                       -- JSON: 变更评分、测试结果等
    UNIQUE(session_id, turn_id)
);
```

- `turn_id → commit_hash` 映射
- `summary` 全文用于自然语言搜索
- `metadata` 存储变更评分、测试结果，用于精细检索

### 回滚执行逻辑

```python
def rollback_to_turn(turn_id: int, session_id: str):
    # 1. 从 CheckpointStore 获取该 turn_id 对应的 commit_hash
    row = db.query(
        "SELECT commit_hash FROM checkpoints WHERE turn_id = ? AND session_id = ?",
        turn_id, session_id
    )
    if not row:
        return {"error": f"turn_{turn_id} 无 checkpoint"}

    # 2. git restore 恢复文件（不影响用户 Git）
    subprocess.run([
        "git", "--git-dir=.flypig_checkpoints/.git",
        "--work-tree=.", "restore", "--source=" + row.commit_hash, "."
    ], cwd=workspace_root)

    # 3. 清理未跟踪的文件
    subprocess.run(["git", "clean", "-fd"], cwd=workspace_root)

    # 4. 通过 WebSocket 推送事件，前端刷新文件树
    event_bus.emit("workspace:updated", {"session_id": session_id})
```

### 与用户 Git 的隔离

Agent Git 使用隐藏目录 `.flypig_checkpoints/`，通过 `--git-dir` 和 `--work-tree` 操作：

```bash
# 首次使用时自动初始化（GitCheckpointManager 自动完成，无需手动执行）
git --git-dir=.flypig_checkpoints/.git --work-tree=. init --separate-git-dir=.flypig_checkpoints/.git .

# 每次 checkpoint
git --git-dir=.flypig_checkpoints/.git --work-tree=. add -A
git --git-dir=.flypig_checkpoints/.git --work-tree=. commit -m "[turn_3] ..."

# 回滚
git --git-dir=.flypig_checkpoints/.git --work-tree=. restore --source=<hash> .
git --git-dir=.flypig_checkpoints/.git --work-tree=. clean -fd
```

用户 Git 完全不受影响——`git status` 看不到 Agent 的 commit，`git log` 也不包含 Agent 的提交记录。

**MVP 阶段简化**：暂不隔离用户 Git。Agent 直接用工作区做 `--work-tree`，告知用户"Agent checkpoint 可能影响你的 git status"。正式版实现完整隔离。

### 自然语言回滚

```python
async def rollback_by_natural_language(user_query: str, session_id: str):
    # 1. 获取该 session 所有 checkpoints（turn_id, summary, commit_hash）
    checkpoints = db.query(
        "SELECT turn_id, summary, commit_hash FROM checkpoints WHERE session_id = ?",
        session_id
    )

    # 2. 语义搜索或关键词匹配
    best = semantic_search(user_query, [cp.summary for cp in checkpoints])

    if best.confidence >= 0.8:
        rollback_to_turn(best.turn_id, session_id)
        return f"已回滚到：{best.summary}"
    else:
        # 出选择题让用户选择
        candidates = [
            {"id": cp.turn_id, "label": cp.summary}
            for cp in checkpoints[:5]
        ]
        return {"type": "choice_card", "question": "请选择要回滚到的状态", "options": candidates}
```

### 新增模块

| 模块 | 职责 |
|------|------|
| `GitCheckpointManager` | 封装 Agent Git 的初始化、commit、restore |
| `CheckpointStore` | SQLite 映射表 CRUD（turn_id → commit_hash） |
| `SummaryGenerator` | 根据本轮交互生成短语摘要（规则或小模型，≤ 50 字符） |
| `POST /api/rollback/<turn_id>` | 根据 turn_id 回滚工作区 |
| `POST /api/rollback/search` | 接受自然语言，返回匹配的 turn_id 列表或 choice_card |
| 前端 Dashboard "回滚点时间线" | 展示摘要列表，供用户直接点击回滚 |

### 前端感知

回滚后后端通过 WebSocket 发送 `workspace:updated` 事件：

```
event: workspace:updated
data: {"session_id": "abc123"}
```

前端收到后：
- 重新加载文件树
- 刷新已打开的文件内容
- 当前编辑文件如有变化，提示"文件已被回滚，是否重新加载？"

### 自然语言回滚精度优化（P2 规划）

三层兜底策略，不追求一次猜对：

**第一层：结构化摘要**
SummaryGenerator 产出结构化元数据而非纯文本：

```python
@dataclass
class CheckpointMeta:
    title: str                    # 简短标题
    tags: list[str]               # 标签
    files_changed: list[str]      # 变更文件列表
    dialogue_type: str | None     # file_change / ask_choice / discussion
```

用户说"回到改 auth 之前" -> tags + files_changed 直接匹配。

**第二层：变更时间线**
多匹配时不弹选择题，展示结构化时间线：

```
  1. turn_5 · 新增 login 函数参数校验     · 10 分钟前
  2. turn_3 · 重构 auth 模块              · 30 分钟前
  3. turn_1 · 创建 auth.py               · 1 小时前
```

**第三层：兜底**
匹配不到时提示用户换描述或手动输入 turn_id。

**P0 阶段保持当前方案不变**，以上在需要时再实现。

## 审批分类

| 分类 | 场景 | 典型操作 | 前端渲染 |
|------|------|---------|---------|
| `file` | 文件操作 | 删除/覆盖/编辑关键文件 | 显示 diff 预览 |
| `terminal` | 终端执行 | 运行高风险命令（rm -rf, 格式化磁盘） | 显示命令全文 + 影响范围 |
| `git` | Git 操作 | 回滚/强制推送/重置 | 显示 commits 差异 |
| `test` | 测试相关 | 运行测试套件 | 显示测试范围和预计耗时 |

## 审批流程（伪装成 tool_call）

审批请求不发送自定义 SSE 事件，而是伪装成 `tool_call`，让 Vercel AI SDK 的 `useChat.onToolCall` 原生处理：

```
后端 SSE → {"type":"tool_call", "name":"_ask_approval",
             "arguments":{
               "category": "file",
               "tool": "delete_file",
               "params": {"path": "main.py"},
               "diff": "+ import os\n- old_code()",
               "prompt": "确认修改 main.py？"}}

前端 useChat.onToolCall 正常收到（无需自定义事件处理）
  → ToolCallCard.vue 根据 name=="_ask_approval" 渲染审批卡片:
    [file]    显示 diff 对比 + [批准] [拒绝]
    [terminal]显示命令全文 + 影响范围 + [允许] [拒绝]
    [git]     显示 commits 差异 + [批准回滚] [取消]
    [test]    显示测试范围 + [运行] [跳过]

用户点击 [批准] → useChat.append({role:"user", content:"APPROVE:write_file:main.py"})
后端通过审批 → 恢复挂起的 LangGraph 工具调用
```

## 权限规则（Casbin）

```python
# infrastructure/policies/casbin_setup.py
import casbin
enforcer = casbin.Enforcer("model.conf", "policy.csv")

def check_permission(tool: str, params: dict) -> str:
    """返回 'allow' / 'ask' / 'deny'"""
    obj = f"{tool}:{params.get('path', '')}"
    if enforcer.enforce("ai", obj, "exec"):
        return "allow"
    elif enforcer.enforce("ai", obj, "ask"):
        return "ask"
    return "deny"
```

采用 Casbin (pycasbin) 作为权限引擎。用户通过对话配置规则动态更新策略。规则过多时使用数据库 adapter（非纯 CSV），AI 辅助生成新策略规则。

### 默认 policy.csv 示例

```csv
p, ai, write_file:.zshenv, deny
p, ai, write_file:.zlogin, deny
p, ai, write_file:.zprofile, deny
p, ai, write_file:.bashrc, deny
p, ai, write_file:.bash_profile, deny
p, ai, write_file:.npmrc, deny
p, ai, write_file:.yarnrc, deny
p, ai, write_file:bunfig.toml, deny
p, ai, write_file:.bazelrc, deny
p, ai, terminal:rm -rf /, deny
p, ai, git:push --force, ask
p, ai, terminal:git push --force, ask
p, ai, file:delete *, ask
p, ai, terminal:rm *, ask
```

> 规则读法：`p, 主体, 对象, 动作`
> `deny` = AI 不能执行（除非用户明确要求并显式批准）
> `ask` = AI 执行前弹审批卡片
> 未匹配的规则默认 `allow`（AI 可以直接执行）

## 测试集成 API

```
开发完成 → Agent 进入 REVIEWING 状态
→ PromptManager 切换到 tester 身份
→ 运行测试（tool_bash("pytest")）
→ 测试结果喂给 AI
  ├── 全部通过 → 自动切回 developer，继续下一步
  └── 有失败 → 分析失败原因，修复后重新审查

用户也可以手动触发:
  "帮我跑一下测试" → Agent 切换 tester 身份 → 执行测试
```

## WebSocket

- `/ws/pty/<term_id>` — 用户手动终端（独立于 AI 对话，互不干扰）
