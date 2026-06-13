# 数据流

> **来源**: `architecture-refactor.md` §8
> **关联文档**: `api-reference.md`（事件格式）、`frontend-arch.md`（前端消费）、`usage-tracking.md`（response_end 用量摘要）、`plan-task-system.md`（任务数据流）
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
  ├── type: "reasoning"            → AI 推理过程（灰字斜体）
  ├── type: "choice"               → Explore 选择题卡片
  ├── type: "task_update"          → 任务状态变更（创建/更新/取消）
  ├── type: "tasks_restored"       → 回溯后的任务快照
  ├── type: "change_plan"          → 变更计划（改前预览，逐项批准）
  ├── type: "change_review"        → Execute 变更审查卡片
  ├── type: "suggestion"           → 对抗建议卡片（SSE 事件名为 suggestion）
  └── type: "response_end"         → 结束 + usage

  # approval 不走自定义 SSE 事件——伪装成 tool_call name="_ask_approval"
  # 让 Vercel AI SDK useChat.onToolCall 原生处理
  # 详见 api-reference.md → 审批流程
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
用户"前面改出问题了，回到之前能运行的状态"
  → AI 搜索 IConversationStore.get_summaries() 所有轮次摘要
    → 语义匹配找到最可能的 turn
  ├── 置信度 ≥ 80% → 直接回滚
  └── 不明确 → 出 choice_card 让用户选：
      ┌─────────────────────────────────────┐
      │ 请选择要回滚到的状态：                │
      │  ○ 第 3 轮 - 修改 auth.py，登录功能   │
      │  ○ 第 2 轮 - 新增用户模型，测试通过   │
      │  ○ 第 1 轮 - 项目初始化               │
      └─────────────────────────────────────┘
  → 用户选择 → GitCheckpointManager.restore()
    → git --git-dir=.flypig_checkpoints restore --source=<hash>
    → WebSocket 推送 workspace:updated 事件
  → 前端重新加载文件树 + 刷新编辑器内容
```

## 崩溃恢复数据流

```python
# 每工具调用后自动 checkpoint
tool:after (TurnCheckpointHook)
  └── store.save_checkpoint(session_id, turn_id, partial=True)
       └── SQLite 写入 checkpoints.partial=1

# 进程启动时恢复检测
__main__py:
  └── init_logging()             ← 先初始化日志
  └── check_recovery()           ← 查 partial=True 的轮次
       ├── 无 partial → 正常启动
       └── 有 partial → SSE 推送 recovery 事件
            └── 前端 RecoveryDialog:
                 ├── [继续] → 恢复 AgentState + 提示"已恢复"
                 └── [放弃] → 删除 partial checkpoint
```

## 日志数据流

```python
# 初始化
__main__.py --debug
  └── init_logging(debug=True)
       ├── loguru.add(file sink)    ← ~/.flypig/logs/flypig_YYYY-MM-DD.log
       │     rotation=10MB, retention=30d
       └── loguru.add(stderr sink)  ← 控制台带色输出

# 运行时
chat_node → logger.info("[trace={}] ...")
tool_exec  → logger.debug("[trace={}] tool_call: {}", trace_id, tool_name, args)
异常       → logger.exception("[trace={}] 工具异常", trace_id)
```

## 终端数据流
用户手动终端: xterm.js → WebSocket /ws/pty → terminal.py → 真正 PTY
AI subprocess: ChatService → LangGraph ToolNode → subprocess.communicate()
  → 结果返回 LLM + 可选在终端面板创建只读标签
```
