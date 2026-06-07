# API 参考

> **来源**: `architecture-refactor.md` §3.1, §3.8.2-3.8.5, §8.3
> **关联文档**: `frontend-arch.md`（前端消费）、`data-flow.md`（数据流）
> 新增端点或改 SSE 事件格式时，需同步检查 frontend-arch.md 和 data-flow.md。

## REST 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | SSE 流式对话 |
| `/api/config` | GET/PUT | 配置查询/修改 |
| `/api/files` | GET | 文件列表 |
| `/api/file` | GET | 文件内容 |
| `/api/tree` | GET | 文件树 |
| `/api/sessions` | GET | 历史会话 |
| `/api/health` | GET | 健康检查 |
| `/api/upload` | POST | 文件上传 + 解压 |
| `/api/rollback/<turn_id>` | POST | Git 回滚 |
| `/api/history/search` | GET | 历史搜索 |

## SSE 事件格式（/api/chat）

| 事件类型 | 说明 | 触发时机 |
|----------|------|---------|
| `token` | 逐 token 文本 | LLM 流式输出 |
| `choice` | 选择题卡片 | Explore 模式 |
| `approval` | 审批卡片 | Plan 模式确认/修改 |
| `change_review` | 变更审查卡片 | Execute 执行后 |
| `suggestion` | 对抗建议卡片 | 变更评分后 |
| `response_end` | 结束 + usage | 本轮结束 |

```python
# token 事件（逐 token 推流）
{"type": "token", "content": "每个"}

# response_end 事件
{"type": "response_end", "usage": {"prompt_tokens": 100, "completion_tokens": 50}}

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

## Git 回滚（与 turn_id 挂钩）

每轮对话生成一个 `turn_id`，AI 写文件后自动执行 git commit：

```python
# Prompt 引导 AI 在每次文件变更后执行:
#   git add -A && git commit -m "turn_3: 实现用户登录功能"

# 用户说"回退到第 2 轮":
#   后端执行 git revert HEAD~N（N = 当前轮次 - 目标轮次）
#   恢复对话状态到 turn_2 结束时的 messages 快照
#   更新 ConversationState 为 ROLLED_BACK
```

| 组件 | 职责 |
|------|------|
| Prompt | 引导 AI 在文件变更后自动 git commit -m "turn_N: ..." |
| ChatService | 维护 turn_id 计数器 + 每轮 messages 快照 |
| tool_bash | 执行 git 命令（commit / revert / log） |
| 新增 API | `POST /api/rollback/<turn_id>` 一键回滚 |

## Git Diff 预览（文件变更审批时附带）

每次写文件/编辑文件的工具调用，在执行前通过 `git diff` 获取变更内容：

```
写文件前 → tool_bash("git diff <file>") → 获取增量变更
审批卡片附带 diff 内容 → 用户看到"改了哪里"再决定
执行后 → git add + git commit -m "turn_N: ..."
```

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
