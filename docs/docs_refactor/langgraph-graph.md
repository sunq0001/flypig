# LangGraph 状态图

> **来源**: `architecture-refactor.md` §3.2, §3.3, §3.6.2-3.6.6, §3.8.1, §3.11
> **关联文档**: `mode-matrix.md`（模式权限）、`adversarial-system.md`（对抗节点）、`resilience.md`（崩溃恢复/partial checkpoint）
> 修改 router 或节点定义时，需同步检查 mode-matrix.md 中的权限矩阵。

## 一张图，统一 Graph

不是三张独立图，是所有节点在同一个 StateGraph 内。LLM 通过条件边自行决定路径。

模式不是三种不同的图，只是三种不同的 **context 约束**（工具列表、温度、身份提示词）。

## 全路径一览

核心思想：**AI 自行决定路径**（条件路由），但每条路径的后续流程是确定的（固定边）。

### 前提：任何修改前都要读代码

用户说"改代码"，AI 不是立刻改——先在 **chat 内循环读代码**，读够了再决定走哪条路：

```
用户 → "把登录优化一下"
               ↓
┌── chat（读代码循环）──────────────────────┐
│  第 1 轮: 读 main.py                      │
│  第 2 轮: 搜 "login" 相关文件             │
│  第 3 轮: 读 login.vue 看表单逻辑          │
│  ...（AI 自己控制读多少轮）                │
└────┬──────────────────────────────────────┘
     ↓ AI 说："读明白了，需要改 3 个文件"
```

读代码和改代码是两件事，但都在 chat 节点内解决——AI 用 `read_file` / `search`（未来加知识图谱、向量库）读完，自己判定"可以了"，才走路径 B。

**理解层扩展点** — chat 节点的工具列表是动态的，未来加知识源只需加工具：

```
当前 chat 可用工具:     P1 加知识图谱后:      P2 加向量库后:
├── tool_file.read      ├── + kg_query        ├── + vector_search
├── tool_search         ├── + kg_get_related   ├── + semantic_search
└── tool_project_scan   └── + ...              └── + ...
  仅本地文件搜索         代码结构理解          语义理解
```

LangGraph 的 ToolNode 天然支持动态工具列表——不同模式透传不同工具集。未来加知识源 = 在 `infrastructure/tools/` 下加一个工具文件 + 注册到对应模式的工具列表。`chat` 节点代码不用改。

```
用户输入 / 上一轮回到 chat
    ↓
┌──────────────────────────────────────────────────────┐
│                  chat（分析需求）                       │
│                                                        │
│  chat 做的事情（AI 自主决定做多少，反复循环）：          │
│  ├── 读文件（tool_file.read）                           │
│  ├── 搜代码（tool_search）                              │
│  ├── 查知识图谱（知识库工具）                             │
│  ├── 查向量库（语义检索）                                │
│  ├── 分析运行日志（tool_bash）                           │
│  └── 直接回答（无工具调用）                              │
│                                                        │
│  ★ 多条工具调用 = 多轮 chat 内循环，不是一次决定         │
│  ★ 读够了 → AI 自己判定走哪条路                          │
└──────────────────────────────────────────────────────┘
    │
    ├──→ [路径 A] 直接回答 — 无工具调用，纯文本回复
    │     用户问"Python 怎么排序" → AI 直接回答
    │     → 继续循环 / 任务完成 → 结束
    │
    ├──→ [路径 B] 修改代码 — AI 要改文件
    │     ├──→ [子链 B1] 计划 + 执行（正常修改）
    │     │     change_plan（AI 输出修改方案）
    │     │       ↓
    │     │     ChangeSummary 卡片（需求级，默认折叠）
    │     │       ↓
    │     │     ┌──→ 用户逐项接受 → 子链 B2
    │     │     ├──→ 用户逐项驳回 → 回到 chat，AI 重想
    │     │     ├──→ 部分接受/部分驳回 → 子链 B2（只改接受的）
    │     │     └──→ 用户说"说详细点" → AI 展开解释 → 回到卡片
    │     │
    │     └──→ [子链 B2] 执行流水线（确定链路）
    │           execute（调工具改代码 + 自带 intent/changes）
    │              ↓
    │           lint（自动规范检查）
    │              ↓
    │           change_review（对比计划与实际）
    │              ↓
    │           suggestion（对抗性建议）
    │              ↓
    │           ← 回到 chat，准备下一轮
    │
    ├──→ [路径 C] 出选择题 — AI 需要用户做选择
    │     ask_choice
    │       ↓
    │     用户选择 → 回到 chat
    │
    ├──→ [路径 D] 审批 — 高敏感操作（写文件、删文件、改 git、terminal 高危命令）
    │     approval（伪装成 tool_call，让用户确认）
    │       ↓
    │     ┌──→ 用户批准 → 执行操作
    │     └──→ 用户拒绝 → 不执行，回到 chat
    │
    ├──→ [路径 E] 工具执行错误 — 工具调用失败
    │     错误信息原样返回 AI
    │     AI 自行判定：
    │     ├──→ 重试（参数不同）
    │     ├──→ 换工具
    │     ├──→ 告诉用户"这个操作不可行"
    │     └──→ 问用户怎么办 → 走路径 C
    │
    ├──→ [路径 F] 执行被用户打断 — 用户中途说"停"
    │     stop 信号注入 AgentState
    │     AI 停止当前工具，回到 chat 等待新指令
    │
    ├──→ [路径 G] 滚动回退 — lint 或 review 发现问题
    │     如果 lint 失败 → 自动尝试修复 → 重检
    │     如果 review 发现实际改动 ≠ 计划
    │       └──→ 回到 execute，AI 重新调整
    │
    └──→ [路径 H] 任务完成 → 结束
```

### 子链详解

#### 子链 B2（执行流水线）的详细状态

```
execute（调 write/edit 工具，自带 intent + changes 参数）
  │
  ├──→ 成功 → lint
  │            ├──→ 通过 → change_review
  │            └──→ 失败 → 自动修复 → 再 lint
  │                           └──→ 修不好 → 回到 chat（告诉用户）
  │
  change_review（对比 change_plan 时定的目标和实际结果）
  │
  ├──→ 匹配 → suggestion
  └──→ 不匹配 → 回到 execute（AI 自行补修）
  
  suggestion（从反方角度评估）
  │
  └──→ 回到 chat，由 AI 判定是否需要给用户看
```

#### 路径 E（工具错误）的详细分支

```
tool_bash("rm -rf /") → PermissionChecker 拦截
  ↓
approval 节点 → 用户确认
  ├──→ 批准 → 执行
  └──→ 拒绝 → 不执行

tool_bash("pip install pkg") → 网络超时
  ↓
错误信息回到 AI
  ├──→ AI 重试（加 --timeout 60）
  ├──→ AI 换源（--index-url https://...）
  └──→ AI 告诉用户"网络不稳定，请手动安装"

tool_file.write → 磁盘满
  ↓
  AI 检测到错误 → 告诉用户 → 等待用户处理
```

### 人机分工

```
👤 用户做（决策层）：
├── 提需求
├── 看 ChangeSummary 卡片 → 逐项接收/驳回
├── 回答选择题
├── 审批高敏感操作
├── 中途喊停
└── 不满意 → 继续提需求

🤖 AI 做（执行层）：
├── 分析需求（读文件、搜代码、查知识图谱/向量库）
├── 规划修改方案 → 生成 ChangeSummary 卡片
├── 执行代码修改（自带意图 + 每行注释）
├── 自动 lint + 修复
├── 对比审查
├── 对抗性建议
├── 工具自愈（失败重试/换方案）
└── 循环直到用户满意 / 任务完成

📋 ChangeSummary 卡片 = 人机分界线
   AI 输出结构化报告 → 用户做决策 → AI 按决策执行

🚫 AI 不做：
- 不要用户确认就直接改代码
- 不要被拒绝后坚持不改
- 不要把用户反馈当耳边风继续同一方案
```

### 路径汇总速查

| 路径 | 触发条件 | AI 决定 | 用户参与 |
|------|---------|--------|---------|
| A 直接回答 | 用户问问题，无工具需要 | ✅ | ❌ |
| B 修改代码 | AI 认为需要改文件 | ✅ | ✅ 逐项卡片确认 |
| C 出选择题 | AI 需要用户选项 | ✅ | ✅ 选答案 |
| D 审批 | 高敏感操作 | ⚠️ PermissionChecker | ✅ 确认/拒绝 |
| E 工具错误 | 工具调用失败 | ✅ 自愈或问用户 | ⚠️ 自愈失败才需要 |
| F 用户打断 | 用户中途说停 | ❌ 被中止 | ✅ 主动触发 |
| G 滚动回退 | lint/review 发现问题 | ✅ 自动 | ❌ |
| H 任务完成 | AI 判定目标达成 | ✅ | ❌ |

> **整个图除了「开始」和「结束」，其余全部是循环**。AI 从 chat 出发，无论走哪条路径（调工具 / 出题 / 审批 / 继续想），最终都回到 chat，反复循环。**只有 AI 判断任务完成后，才从 chat 走向结束，循环终止**。

> **变更叙事（change_summary）不需要独立节点**：AI 在调 write/edit 工具时自带 `intent` 和 `changes` 参数，工具执行后直接返回结构化 JSON。前端收到所有 `tool_result` 后聚合渲染 ChangeSummary 卡片。详见 `chat-ux.md` → ChangeSummary 组件。

## 节点定义

| 节点 | 职责 | 边类型 | 所属层 | 文件 |
|------|------|--------|--------|------|
| `chat` | LLM 对话（所有路径起点） | **条件边**（router 路由） | Domain | `domain/agent/nodes.py` |
| `change_plan` | 输出结构化变更方案，用户逐项批准后才执行 | **条件边**（AI 输出修改计划时触发） | Domain | `domain/agent/nodes.py` |
| `ask_choice` | Explore：出选择题 | **条件边**（router 检测 tool_call） | Domain | `domain/agent/nodes.py` |
| `execute` | 调工具（ToolNode） | **条件边**（router 检测 tool_call） | Domain | `domain/agent/nodes.py` |
| `lint` | 自动格式化 | **固定边**（execute → lint 自动触发） | Domain | `domain/agent/nodes.py` |
| `change_review` | 变更后审查（对比变更计划与实际结果） | **固定边**（lint → change_review 自动触发） | Domain | `domain/agent/nodes.py` |
| `suggestion` | 对抗建议 | **固定边**（change_review → suggestion 自动触发） | Domain | `domain/agent/nodes.py` |
| `approval` | 审批（伪装成 tool_call） | **条件边**（router 检测 pending_approval） | Domain | `domain/agent/nodes.py` |
| **图构建** | 编译 StateGraph（导入 nodes + router） | — | **Application** | `application/services/graph_factory.py` |

> **回滚（ROLLBACK）不是独立节点**：回滚由 AI 在 execute 节点内通过 `tool_bash` 调用 git 命令实现，或用户通过 `/api/rollback` API 触发 GitCheckpointManager。不需要专门的 LangGraph 节点。

## Router（路由）

```python
def router(state: AgentState) -> str:
    """基于 LLM 工具调用的条件路由。
    
    AI 决定下一步走向——不是系统硬编码的判断：
    - 有 tool_call 且名为 ask_choice → 走选择题节点（Explore 模式）
    - 有其他 tool_call → 走 execute 节点执行工具
    - 有待审批请求 → 走 approval 节点
    - 无任何条件匹配 → 默认留在 chat 节点（AI 继续思考/输出文本）
    """
    last_msg = state["messages"][-1]
    if last_msg.get("tool_calls") and last_msg["tool_calls"][0]["name"] == "ask_choice":
        return "ask_choice"
    if last_msg.get("tool_calls"):
        return "execute"
    if state.get("pending_approval"):
        return "approval"
    return "chat"
```

### 重复操作检测

检测连续多轮完全相同操作（工具+参数+结果一致）来识别死循环：

```python
def _detect_repeated_actions(state: AgentState, max_repeat: int = 5) -> bool:
    recent = state["messages"][-(max_repeat * 2):]
    if len(recent) < max_repeat * 2:
        return False
    tool_msgs = [m for m in recent if m.get("role") == "tool"][-max_repeat:]
    if len(tool_msgs) < max_repeat:
        return False
    return all(m.get("content") == tool_msgs[0].get("content") for m in tool_msgs)
```

在 `chat_node` 中调用，检测到重复操作时提示用户而非强制中止。

### 节点异常保护

每个节点用 try-except 包裹，防止单个节点崩溃导致整图中断：

```python
def safe_node(node_func):
    """装饰器：节点异常时不崩图，返回错误状态"""
    async def wrapper(state):
        try:
            return await node_func(state)
        except ModelAPIError:
            return {"messages": [AIMessage(content="模型服务暂不可用，请稍后重试")]}
        except Exception as e:
            return {"messages": [AIMessage(content=f"处理出错: {str(e)[:200]}")], "error": str(e)}
    return wrapper
```

所有关键节点（chat、execute、change_review）都应用 `@safe_node`。

### 并发会话隔离

每个会话使用独立的 `graph.compile()` 实例，防止多会话状态污染：

```python
class GraphFactory:
    _sessions: dict[str, CompiledStateGraph] = {}

    def get_graph(self, session_id: str) -> CompiledStateGraph:
        if session_id not in self._sessions:
            self._sessions[session_id] = self._build_graph()
        return self._sessions[session_id]
```

## AgentState（domain/agent/state.py）

```python
class AgentState(TypedDict):
    messages: list                # 对话消息列表
    turn_id: int                  # 当前对话轮次
    session_id: str               # 会话 ID（关联 ConversationStore）
    persona: str                  # developer/reviewer/tester/...
    mode: str                     # explore / plan / execute
    pending_approval: dict | None # 待审批请求
    change_review: dict | None    # 变更审查数据
    rejected_changes: list | None # 被用户驳回的变更
    change_score: dict | None     # 变更评分结果
    adversarial_suggestion: dict | None  # 对抗建议卡片（含 suggestion_id）
    test_results: str | None      # 测试结果
    git_snapshot: str | None      # Git 快照（用于回滚）
    active_tasks: list | None     # ★ 当前会话活跃任务列表（TaskItem[] 已序列化）
```

> 新增 `session_id` 字段，用于与 ConversationStore 关联。`active_tasks` 用于在对话中传递当前活跃任务列表，Turns 间保持任务上下文。

## chat_node 集成 ContextPipeline

```python
# domain/agent/nodes.py
from di.container import Container

def chat_node(state: AgentState) -> dict:
    pipeline = Container.get("context_pipeline")
    store = Container.get("conversation_store")

    # 1. 压缩上下文（读 store → 压缩 → 返回消息列表）
    user_input = state["messages"][-1]["content"]
    context = await pipeline.build(
        store=store,
        session_id=state["session_id"],
        user_input=user_input,
    )

    # 2. 调 LLM
    response = llm.invoke(context)
    state["turn_id"] += 1

    # 3. 存本轮完整记录到 store
    await store.save_turn(
        session_id=state["session_id"],
        turn_id=state["turn_id"],
        data=TurnRecord(
            user_message=user_input,
            ai_response=response.content,
            # ... tool_calls, suggestions 等从 state 中取
        ),
    )

    return {
        "messages": [response],
        "turn_id": state["turn_id"],
    }
```

### 字段生命周期

| 字段 | 写入节点 | 读取节点 | 说明 |
|------|---------|---------|------|
| `messages` | chat, execute, approval | router, chat | AI 对话历史，所有节点可追加 |
| `turn_id` | chat_node（每轮+1） | 全局 | 每轮对话自增，用于 checkpoint 和回滚 |
| `persona` | PromptManager.switch | chat, suggestion | developer/reviewer/tester/architect/documenter |
| `mode` | chat_node（AI 或用户选择） | 全局 | explore / plan / execute，决定 context 约束 |
| `pending_approval` | approval_node | router, approval | 待审批请求，非空时 router 自动导向 approval |
| `change_review` | change_review_node | 前端渲染 | 变更审查数据，输出后由用户逐项确认 |
| `rejected_changes` | 前端驳回回调 | chat_node | 用户驳回的变更列表，AI 分析后提替代方案 |
| `change_score` | change_review_node | suggestion_node | 变更评分，决定对抗建议的级别和内容 |
| `adversarial_suggestion` | suggestion_node | 前端渲染 | 对抗建议卡片，用户勾选后执行 |
| `test_results` | execute（AI 跑测试后） | chat_node | 测试输出，用于判断是否需要修复 |
| `git_snapshot` | chat_node（每轮开始） | rollback | 当前工作区 Git 概览，用于回滚参考 |

## DynamicToolNode（MCP 热插拔）

MCP 工具热加载需要动态工具列表。推荐方案 A，MCP 工具不会每轮对话变化。

### 方案 A（推荐——编译时已知工具集 + 出错时重建）

```python
class DynamicGraphFactory:
    """工具变化时重建 LangGraph，不追求每轮动态"""

    def __init__(self, executor: IToolExecutor):
        self.executor = executor
        self._graph = None
        self._last_tool_hash = None

    def get_graph(self) -> CompiledStateGraph:
        current_hash = hash(tuple(self.executor.get_tools_schema()))
        if self._graph is None or current_hash != self._last_tool_hash:
            self._graph = self._build_graph()
            self._last_tool_hash = current_hash
        return self._graph

    def _build_graph(self) -> CompiledStateGraph:
        tools = self.executor.get_available_tools()  # 含 MCP 动态注册的工具
        tool_node = ToolNode(tools)
        workflow = StateGraph(AgentState)
        # ... 注册所有节点和条件边 ...
        workflow.add_node("execute", tool_node)
        return workflow.compile()
```

### 方案 B（v2 可选——自定义 ToolNode 每轮动态获取）

```python
class DynamicToolNode:
    def __init__(self, executor: IToolExecutor):
        self.executor = executor

    def __call__(self, state: AgentState) -> dict:
        from langgraph.prebuilt.tool_executor import ToolExecutor as LangGraphToolExecutor
        tools = self.executor.get_available_tools()  # 每次都动态获取
        executor = LangGraphToolExecutor(tools)
        last_message = state["messages"][-1]
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": state["messages"]}
        results = []
        for tc in last_message.tool_calls:
            try:
                result = executor.execute(tc)
                results.append(result)
            except Exception as e:
                results.append(ToolMessage(
                    content=f"工具执行失败: {str(e)}",
                    tool_call_id=tc["id"],
                ))
        return {"messages": results}
```

## 三种模式的 context 对比

| 维度 | Explore Context | Plan Context | Execute Context |
|------|:--------------:|:-----------:|:--------------:|
| **温度** | 0.1-0.2（严谨引导） | 0.2（结构化输出） | 0.3-0.5（自由发挥） |
| **可用工具** | `ask_choice`, `search`, `read`, `write_file`(仅文档/配置) | `ask_choice`, `search`, `read`, `write_file`(仅文档/配置) | 全部工具 |
| **Prompt 身份** | 需求分析师 | 规划师 | 执行者 |
| **LangGraph 节点** | 全部条件边，AI 自行跳转 | 全部条件边，AI 自行跳转 | 全部条件边，AI 自行跳转 |
| **Human-in-loop** | 选项点击/自定义输入 | 审批卡片 | 审批卡片（按需） |
| **终止条件** | 需求足够清晰 | 用户确认方案 | 任务完成或切回 Explore |

## Plan Mode 工作流

AI 先调研输出结构化方案，通过审批卡片让用户确认/修改，确认后切换 Execute 执行。

```
Plan Mode Context:
  temperature=0.2  |  tools=只读(search/grep/read)  |  prompt=规划师

     ┌───── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
     │    所有子链由 AI 自行选择跳转                   │
     │  ┌──────────┐   ┌────────────────┐            │
     │  │ 调研阶段  │   │  方案输出       │            │
     │  │ (search, │←─→│ (结构化文本)    │            │
     │  │  read)   │   └───────┬────────┘            │
     │  └──────────┘           │                     │
     │                    ┌────▼────────┐            │
     │                    │ 审批卡片      │            │
     │                    │ (human-in-   │            │
     │                    │  the-loop)   │            │
     │                    └──┬────┬─────┘            │
     │              ┌─────────┘    │                  │
     │              ▼              ▼                  │
     │          修订方案     等待用户指令               │
     │          (回到调研)    (手动确认执行)            │
     └───── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

**关键限制**：Plan 阶段 AI 可使用只读工具 + ask_choice + write_file（限文档/配置如 .md、.yaml、.json），不可修改源代码（.py、.js、.ts、.vue 等）。bash 命令仅限查询。

## Execute Mode 工作流

AI 收到指令直接干活，全部工具可用。

```
Execute Mode Context:
  temperature=0.3-0.5  |  tools=全部  |  prompt=执行者

     ┌───── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
     │    AI 自行选择子链，不是顺序执行                        │
     │  ┌──────────┐    ┌──────────┐    ┌──────────┐         │
     │  │ CLARIFY  │←───│ EXECUTE  │←───│ REVIEW   │         │
     │  │ (快速澄清)│    │ (ToolNode)│    │ (自检)   │         │
     │  └──────────┘    └──────────┘    └────┬─────┘         │
     │        │               │              │               │
     │        ▼               ▼              ▼               │
     │  ┌──────────┐    ┌──────────┐    ┌──────────┐         │
     │  │ ASK_CHOICE│   │ ROLLBACK │    │ ARCHITECT│         │
     │  │ (出选择题)│    │ (git回滚)│    │ (重构评估)│         │
     │  └──────────┘    └──────────┘    └──────────┘         │
     │                                                         │
     │  AI 可以：                                               │
     │  1. 简单快速 → 直接 EXECUTE → DONE                       │
     │  2. 需要调研 → CLARIFY → 调研 → EXECUTE → REVIEW        │
     │  3. 发现问题 → REVIEW → ROLLBACK → 重新 EXECUTE         │
     │  4. 需求模糊 → 主动切回 Explore Mode 出选择题             │
     │  5. 改得太多 → REVIEW → ARCHITECT → 重构 → 再 REVIEW     │
     └───── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
```

执行模式下，AI 如果发现需求不明确，可以主动切入 Explore Mode。

## 审批卡片内容

```json
{
    "type": "approval_card",
    "context": "plan_approval",
    "plan_summary": "创建个人博客系统",
    "steps": [
        "1. 初始化 Vue 3 + Vite 项目",
        "2. 安装 Element Plus + 路由依赖",
        "3. 创建博客路由与基础组件"
    ],
    "estimated_cost": {"tokens": "~8000", "files": "~15个"}
}
```

## PromptManager

多角色 prompt 按需懒加载，不一股脑塞给 LLM。有五个 prompt 角色文件在 `domain/prompts/` 下。

```python
# domain/prompt_manager.py
class PromptManager:
    """按需加载 prompt，不一股脑塞给 LLM"""

    _cache = {}

    def load(self, persona: str) -> str:
        """懒加载，仅首次读取文件"""
        if persona not in self._cache:
            path = Path(__file__).parent / "prompts" / f"{persona}.md"
            self._cache[persona] = path.read_text(encoding="utf-8")
        return self._cache[persona]

    def switch(self, state: AgentState, persona: str, context: dict) -> AgentState:
        """
        切换 Agent 身份。向 LangGraph AgentState 追加一条 system message，
        不覆盖已有消息。保留历史让 LLM 知道上下文。
        """
        prompt = self.load(persona)
        switch_msg = (
            f"[角色切换] 你现在是 {persona}。\n"
            f"当前上下文: {json.dumps(context)}\n"
            f"{prompt}"
        )
        # 追加 system message（不覆盖历史）
        state["messages"].append({"role": "system", "content": switch_msg})
        state["persona"] = persona
        return state

# 5 个 prompt 角色：
# developer.md — 核心开发者身份
# reviewer.md  — 代码审查员（对抗性）
# tester.md    — 测试员
# architect.md — 重构/架构评估
# documenter.md— 文档撰写
```

---

## 配置驱动 DAG（可扩展方案）

> 图拓扑由配置文件声明，代码只负责节点行为和路由逻辑。
> 加新路径 = 改配置文件 1 行 + 加 1 个节点函数，不影响现有路径。

### `graph-config.toml`

```toml
[[nodes]]
name = "chat"
type = "hub"
description = "分析需求，由 LLM 自主决策下一跳"
edges = [
  {to = "direct_answer",  when = "无工具调用"},
  {to = "change_plan",    when = "需要改代码"},
  {to = "ask_choice",     when = "需要用户做选择"},
  {to = "approval",       when = "高敏感操作（PermissionChecker触发）"},
  {to = "end",            when = "用户停止/任务完成"},
]

[[nodes]]
name = "change_plan"
type = "standard"
edges = [
  {to = "execute",  when = "用户全部接受"},
  {to = "chat",     when = "用户全部驳回"},
  {to = "execute",  when = "部分接受/部分驳回"},
  {to = "chat",     when = "用户要求展开解释"},
]

[[nodes]]
name = "execute"
type = "pipeline"
chain = ["lint", "change_review", "suggestion"]
edges = [
  {to = "chat",  when = "pipeline完全通过"},
  {to = "execute", when = "review不匹配→自动补修"},
  {to = "chat",  when = "lint自动修复失败→通知用户"},
]

[[nodes]]
name = "direct_answer"
type = "leaf"
edges = [{to = "end", when = "无后续任务"}]

[[nodes]]
name = "ask_choice"
type = "standard"
edges = [{to = "chat", when = "用户选择完毕"}]

[[nodes]]
name = "approval"
type = "standard"
edges = [
  {to = "execute", when = "用户批准"},
  {to = "chat",    when = "用户拒绝"},
]

[[nodes]]
name = "lint"
type = "pipeline_step"
edges = [{to = "change_review", when = "通过"}]

[[nodes]]
name = "change_review"
type = "pipeline_step"
edges = [{to = "suggestion", when = "匹配"}]

[[nodes]]
name = "suggestion"
type = "pipeline_step"
edges = [{to = "chat", when = "完成"}]

[[nodes]]
name = "end"
type = "terminal"
```

### 构建器 `core/graph_builder.py`

```python
import toml
from langgraph.graph import StateGraph, END

def build_graph_from_config(
    config_path: str = "graph-config.toml"
) -> StateGraph:
    """从配置文件构建 LangGraph"""
    config = toml.load(config_path)
    graph = StateGraph(AgentState)

    # 1. 注册所有节点
    for node_def in config["nodes"]:
        name = node_def["name"]
        graph.add_node(name, get_node_fn(name))  # 从 nodes.py 导入

    # 2. 注册边
    for node_def in config["nodes"]:
        name = node_def["name"]
        edges = node_def.get("edges", [])

        has_fixed = [e for e in edges if "when" not in e]
        has_conditional = [e for e in edges if "when" in e]

        for e in has_fixed:
            graph.add_edge(name, e["to"])

        if has_conditional:
            graph.add_conditional_edges(
                name,
                router,  # 条件判断函数（代码），配置只存目标
                {e["to"]: e["to"] for e in has_conditional},
            )

    return graph.compile()

def get_node_fn(name: str):
    """按名称导入对应节点函数"""
    import domain.agent.nodes as nodes
    return getattr(nodes, f"{name}_node", None)
```

### 加新路径的步骤

```
1. graph-config.toml 加一行:
     [[nodes]]
     name = "new_path"
     edges = [{to = "chat", when = "完成"}]

2. chat 节点的 edges 加一行:
     {to = "new_path", when = "新场景"},

3. router.py 加一个 if 判断:
     if 新场景: return "new_path"

4. domain/agent/nodes.py 加一个函数:
     def new_path_node(state): ...
```

### 与 LangGraph 原生 API 的关系

```
配置文件           代码                  LangGraph 原生 API
 graph-config.toml  core/graph_builder.py  → .add_node()
                                         → .add_edge()
                                         → .add_conditional_edges()
                                         → .compile()

配置管"有哪些节点、怎么连"
代码管"节点函数怎么写、条件怎么判断"
LangGraph 管"运行时状态管理、图执行"
三者不冲突，各司其职。
```
