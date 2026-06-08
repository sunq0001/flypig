# 数据流

> **来源**: `architecture-refactor.md` §8
> **关联文档**: `api-reference.md`（事件格式）、`frontend-arch.md`（前端消费）
> 改数据流时，需同步检查 api-reference.md 中的事件格式。

## 当前（复杂且有问题）

```
用户输入 → POST /api/chat
  → server.py(780行)
    → PTY 注入 7 步链路（AI→SSE→前端→API→WS→PTY）
    → setInterval 模拟流式
  → 前端手写 ReadableStream 解析 + PTY 注入逻辑
```

## 目标（LangGraph + Vercel AI SDK）

```
前端 useChat.handleSubmit()
  → POST /api/chat (SSE)
  → ChatService → LangGraph StateGraph
    → 条件路由（AI 决定下一节点）
    → ToolNode 执行 subprocess
    → 逐 token 推流（LangGraph streaming）
  → Vercel AI SDK 原生消费流式
```

## 后端数据流

```
Vercel AI SDK (前端)
  │ POST /api/chat
  ▼
ChatService (应用层)
  │
  ▼
LangGraph.chat_node (LLM 对话)
  │ LLM 自行判断路径：问问题 / 输出方案 / 调工具
  │ 全部通过条件边在同一张图内完成
  ▼
ask_choice_node / execute_node / chat_node（同一张图内）
  │ context 约束决定工具差异
  ▼
LangGraph StateGraph（领域层）
  │ 所有节点间都是条件边，AI 自行决定跳转
  │
  ├── Explore Context:
  │   子链：[分析需求 | 出选择题 | 收集答案 | 逐步收敛]
  │   工具：仅 ask_choice + search + read + write_file（限文档/配置）
  │   跳转：AI 决定下一步问什么、何时收窄、何时切换 Plan
  │
  ├── Plan Context:
  │   子链：[调研代码 | 输出方案 | 等审批 | 修订方案]
  │   工具：仅只读（search/grep/read）+ ask_choice + write_file（限文档/配置）
  │   跳转：AI 决定调研到什么程度、何时输出方案、如何回应审批
  │
  └── Execute Context:
      子链：[快速澄清 | 执行(ToolNode) | 自检 | 回滚 | 重构评估]
      工具：全部（bash/file/git/test）
      跳转：AI 决定改什么、改完是否自检、发现问题是否回滚、
            改太多是否重构、需求模糊是否切回 Explore
  │
  ▼
SSE 事件流 → Vercel AI SDK 自动渲染
  ├── type: "token"                → 普通文本流式渲染
  ├── type: "choice"               → Explore 选择题卡片
  ├── type: "approval"             → Plan 审批卡片
  ├── type: "change_review"        → Execute 变更审查卡片
  ├── type: "adversarial_suggestion" → 对抗建议卡片（ChangeScore 触发）
  └── type: "response_end"         → 结束 + usage
```

## Checkpoint 数据流

```
AI 执行 write_file/edit_file 等文件变更
  → ToolNode 返回成功
  → GitCheckpointManager 执行 git add -A + commit
    → commit 到 .flypig_checkpoints（独立 Agent Git，不影响用户 .git）
    → CheckpointStore 记录 (turn_id → commit_hash → summary)
  → 写入 SQLite 映射表
```

## 回滚数据流

```
用户说"回到第 3 轮的状态"
  → AI 调用 rollback_by_natural_language()
    → CheckpointStore 查询 turn_id → commit_hash
    → GitCheckpointManager.restore()
      → git --git-dir=.flypig_checkpoints restore --source=<hash>
    → WebSocket 推送 workspace:updated 事件
  → 前端收到后重新加载文件树 + 刷新编辑器内容
```

## 终端数据流

```
用户手动终端: xterm.js → WebSocket /ws/pty → terminal.py → 真正 PTY
AI subprocess: ChatService → LangGraph ToolNode → subprocess.communicate()
  → 结果返回 LLM + 可选在终端面板创建只读标签
```
