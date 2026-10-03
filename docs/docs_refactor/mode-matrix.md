# 三种模式权限矩阵

> 模式不是三张图，是同一张 LangGraph 的三种 **context 约束**。
> 用户选择或 LLM 建议进入某个模式后，系统施加对应的约束（工具列表/温度/身份），LLM 在约束内自行决定调用哪个子链。
>
> **模式不影响图结构**：`langgraph-graph.md` 中的 8 条路径（A-H）在所有模式下一致。
> 模式只影响 `chat_node` 中传给 LLM 的工具列表——Explore 看不到 write_file，自然走不出路径 B。
> 路由拓扑、节点定义、pipeline 流程完全不变。

---

## 核心矩阵：用户要求 × 当前模式

> 横轴 = **当前所处模式**，纵轴 = **用户提出的要求**。
> 单元格说明：在某个模式下，用户提出某种要求时 LLM 该如何响应。

| 当前模式 →<br>**用户要求 ↓** | **Explore** | **Plan** | **Execute** |
|:---|:-----------:|:--------:|:-----------:|
| **Explore**<br>（出选择题、讨论） | ✅ **当前模式**<br>必须调 ask_choice | ✅ **可执行**<br>Plan 中 ask_choice 可用 | ✅ **可执行**<br>Execute 中可直接调 |
| **Plan**<br>（写文案、规划文档） | ✅ **可执行**<br>用户说"直接写文档"可略过 ask_choice | ✅ **当前模式**<br>主要行为，输出方案 | ✅ **可执行**<br>Execute 全权限，LLM 自行决定 |
| **Execute**<br>（写代码、执行命令） | ❌ **提示**<br>"当前是 Explore，要切 Execute 吗？" | ❌ **提示**<br>"当前是 Plan，要切 Execute 吗？" | ✅ **当前模式**<br>全权限 |

### 各模式默认行为说明

| 维度 | **Explore（探讨）** | **Plan（规划）** | **Execute（执行）** |
|------|:------------------:|:---------------:|:------------------:|
| **入口** | 用户说"先讨论一下"/"我不确定" / LLM 建议 | 用户说"先规划一下" / LLM 建议 | 用户说"直接开干"/"帮我写" |
| **默认行为** | 必须调 ask_choice 出选择题 | 输出结构化方案 | 直接执行（调研+代码+审查） |
| **工具列表** | `ask_choice`, `search`, `read` | `ask_choice`, `search`, `read` | **全部工具** |
| **温度** | 0.1-0.2（严谨引导） | 0.2（结构化输出） | 0.3-0.5（自由发挥） |
| **Prompt 身份** | 需求分析师 | 规划师 | 执行者 |
| **切换条件** | 需求清晰后 LLM 可建议切 Plan/Execute | 方案确认后自动切 Execute | 需求模糊时 LLM 可建议切回 Explore |

---

## 工具可用性明细

| 工具 | Explore | Plan | Execute |
|------|:-------:|:----:|:-------:|
| `ask_choice`（出选择题） | ✅ 强制 | ✅ | ✅ |
| `search`（grep / find_files） | ✅ | ✅ | ✅ |
| `read_file` | ✅ | ✅ | ✅ |
| `bash`（执行命令） | ❌ | ❌ | ✅ |
| `write_file`（写文件） | ❌ | ❌ | ✅ |
| `patch_file`（编辑文件） | ❌ | ❌ | ✅ |
| `task_log`（后台日志） | ❌ | ❌ | ✅ |
| `lint`（代码格式化） | ❌ | ❌ | ✅ |
| `change_review`（变更审查） | ❌ | ❌ | ✅ |
| `mcp_*`（外部工具） | ❌ | ❌ | ✅ |
| `extract_archive`（解压） | ❌ | ❌ | ✅ |

---

## 交互示例

### Explore 模式
```
用户: 帮我做个博客系统
  → LLM 出选择题："需要什么类型的博客？[个人][技术][企业]"
用户: 个人博客
  → LLM 继续出题："需要什么功能？[Markdown][评论][标签]"
用户: Markdown + 标签
  → LLM：需求清晰了，要开始规划方案吗？
用户: 好
  → LLM 建议：进入 Plan 模式 | 用户确认
```

### Plan 模式
```
用户: 先帮我规划一下博客系统
  → LLM 调研：搜索现有博客系统代码、读取工作区文件
  → LLM 输出方案：
     1. Vue 3 + Vite 初始化
     2. 安装 Element Plus
     ...
  → 审批卡片 [确认] [修改]
用户: [确认]
  → 自动切换 Execute 模式
```

### Execute 模式
```
用户: 直接干，帮我写个博客
  → LLM 调研后直接写代码
  → 如果需求模糊 → 可主动调 ask_choice 出选择题
  → 自动 lint → 输出变更审查
```

---

## 实现方式（伪代码）

### 1. 模式上下文

```python
# domain/agent/context.py — 模式定义
MODE_CONTEXTS = {
    "explore": ModeContext(
        tools=[ask_choice, search, read_file],
        temperature=0.1,
        persona="需求分析师",
        force_ask_choice=True,  # 默认必须先 ask_choice
    ),
    "plan": ModeContext(
        tools=[ask_choice, search, read_file],
        temperature=0.2,
        persona="规划师",
        force_ask_choice=False,
    ),
    "execute": ModeContext(
        tools=ALL_TOOLS,  # 全部工具
        temperature=0.3,
        persona="执行者",
        force_ask_choice=False,
    ),
}
```

### 2. 主节点 `chat_node`

```python
# domain/agent/nodes.py — chat_node
def chat_node(state: AgentState) -> dict:
    ctx = MODE_CONTEXTS[state["mode"]]   # 当前模式约束
    response = llm.invoke(
        state["messages"],
        tools=ctx.tools,                 # 只传当前模式允许的工具
        temperature=ctx.temperature,
    )

    # ★ 如果 LLM 调了 write/edit 工具，注入 intent 和 changes 参数
    # 这些数据会用于前端 ChangeSummary 卡片渲染
    for tool_call in response.get("tool_calls", []):
        if tool_call["name"] in ("write_file", "patch_file"):
            enrich_change_intent(tool_call)  # 自动补全 intent + changes

    return {"messages": [response]}
```

### 3. 条件路由 `router`

对应 `langgraph-graph.md` 中的 8 条路径：

```python
# domain/agent/router.py — 条件路由
def router(state: AgentState) -> str:
    last = state["messages"][-1]

    # [路径 H] 用户手动停止
    if state.get("user_stop_requested"):
        return "end"

    # [路径 F] 工具执行中断
    if state.get("execution_interrupted"):
        return "chat"

    # [路径 E] 工具执行错误
    if state.get("last_tool_error"):
        return "chat"           # 错误信息已留在 state 中，AI 自行处理

    if last.get("tool_calls"):
        name = last["tool_calls"][0]["name"]

        # [路径 C] 出选择题
        if name == "ask_choice":
            return "ask_choice"

        # [路径 D] 高敏感操作审批
        if name in NEED_APPROVAL_TOOLS:
            return "approval"

        # [路径 B] 修改代码
        if name in CODE_MODIFY_TOOLS:
            # ★ 返回 change_plan 节点，先输出计划 + ChangeSummary 卡片
            return "change_plan"

        # [路径 A] 不可修改工具（search/read），走 execute
        return "execute"

    # [路径 A] 无工具调用 → 直接回答
    return "chat"

# [路径 G] 流水线自动路由（固定边，不走 router）
# execute → lint → review → suggestion 是 pipeline 内部的确定链路
```

### 4. `summarize` 节点（内置于工具）

不需要独立节点。信息在 AI 调 write/edit 工具时自带 `intent` 和 `changes` 参数：

```python
# tools.py — write_file 工具
@tool(name="write_file",
      intent="必填：本次修改的意图说明",
      changes="必填：每个改动的行号和原因")
def write_file(path: str, content: str, intent: str = "",
               changes: list[dict] = None) -> dict:
    """写入文件，自带变更解释"""
    # 执行写入
    result = _do_write(path, content)
    # 返回结构包含 change_summary
    return {
        "success": True,
        "diff": result["diff"],
        "change_summary": {
            "intent": intent,
            "changes": changes or [],
            "lines_added": result["added"],
            "lines_deleted": result["deleted"],
        }
    }

# 前端 EventRouter 收集所有 tool 返回的 change_summary
# → 聚合渲染 ChangeSummary 卡片
```
