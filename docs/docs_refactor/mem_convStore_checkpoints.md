# mem_convStore_checkpoints：Checkpoint 系统

> **来源**: `memories.md`（长期记忆总览）
> **关联文档**: `memories.md`（表结构/接口）、`backend-modules.md`（TurnCheckpointHook）、`data-flow.md`（恢复数据流）、`subprocess.md`（实时停止执行）

## 双层 Checkpoint

| 层级 | 触发时机 | 存储 | 用途 |
|:----:|---------|------|------|
| **turn:checkpoint** | 每完成一个工具调用 | SQLite（turns 表 partial 字段 + LangGraph checkpoints 表） | 崩溃恢复，重启继续 |
| **Git Checkpoint** | 每轮 AI 修改文件后 | git commit + checkpoint_mappings 表 | 文件级回溯 |

## turn:checkpoint（默认启用）

每调完一个工具写一次，SQLite INSERT ~0.1ms。用 `conversations.db` 的 `checkpoints` 表。

```python
@hook("tool:after", priority=50)
class TurnCheckpointHook:
    async def on_event(self, ctx: HookContext):
        store = Container.get("conversation_store")
        state = ctx.state
        await store.save_checkpoint(
            session_id=state["session_id"],
            turn_id=state["turn_id"],
            partial=True,
        )
```

### 崩溃恢复

进程启动时检测 `partial=True` 的轮次：

```python
async def check_recovery():
    store = Container.get("conversation_store")
    partial_turn = await store.get_last_partial_turn()
    if partial_turn:
        return {
            "type": "recovery",
            "session_id": partial_turn.session_id,
            "turn_id": partial_turn.turn_id,
            "summary": "检测到上一轮未正常结束",
        }
    return None
```

### 前端恢复弹窗

```
┌─────────────────────────────────────────┐
│ ⚠️ 检测到上次对话未正常结束               │
│                                          │
│ 在 turn_5 时中断，已执行工具调用:          │
│  ✅ write_file auth.py                    │
│  ✅ tool_bash pip install ...             │
│                                          │
│  [继续对话] [放弃中断的轮次]               │
└─────────────────────────────────────────┘
```

## Git Checkpoint（GitCheckpointManager）

```python
class GitCheckpointManager:
    async def init_repo(self, workspace: str): ...
    async def commit_turn(self, turn_id: int, summary: str) -> str:
        repo = git.Repo(self.workspace)
        repo.index.add("*")
        commit = repo.index.commit(f"[turn_{turn_id}] {summary}")
        store = Container.get("conversation_store")
        store.save_checkpoint_map(turn_id, commit.hexsha, summary)
        return commit.hexsha
    async def restore(self, turn_id: int):
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

## 前端防误刷

输入框内容每次变更写入 localStorage，崩溃后自动恢复：

```javascript
const DRAFT_KEY = `flypig_draft_${sessionId}`
watch(input, debounce((val) => { localStorage.setItem(DRAFT_KEY, val) }, 500))
onMounted(() => {
    const draft = localStorage.getItem(DRAFT_KEY)
    if (draft) showRestoreToast("已恢复上次未发送的输入")
})
```
