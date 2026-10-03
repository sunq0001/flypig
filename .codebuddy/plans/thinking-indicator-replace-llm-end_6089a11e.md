---
name: thinking-indicator-replace-llm-end
overview: 把前端逐条显示的 llm_end token 信息替换为一个统一的「AI 正在思考…」指示器，解决空白 token 跳动的怪异体验。
todos:
  - id: thinking-indicator
    content: "Add thinking indicator: suppress llm_end messages, accumulate tokens internally, show delayed thinking animation, append token summary to final response"
    status: completed
---

## 产品概述

修复 AI 思考阶段的前端显示问题。把原始的 tool_call 和 llm_end 替换为人类可读的工具说明 + 思考指示器。内部 agent 文件（flypig/ 等）不显示。

## 核心需求

1. 恢复非 bash 工具的 tool_call 显示，但改为**人类可读的说明文字**（如 "📖 正在读取文件 interactive.py"）
2. **过滤内部文件**：路径含 `flypig/`、`.codebuddy/` 的不显示
3. 消除 `llm_end` 作为独立消息，改为内部累计，最终追加到回复底部
4. 空白期（AI 在思考但无任何可见输出）显示思考指示器（延迟 500ms）
5. 命令卡片 + 工具说明 + 最终回复构成完整的可见流程

## 技术方案

### 修改文件

1. `flypig/web/server.py` — `_SseHook.on_tool_start()` 生成 `label` 字段
2. `flypig/web/static/index.html` — 显示逻辑重写

### 实施要点

#### 1. 后端：`server.py` `_SseHook.on_tool_start()` 生成工具标签

```python
def _tool_label(name: str, args: dict) -> str | None:
    path = (args.get("path") or args.get("filePath") or "").replace("\\", "/")
    # 内部文件不显示
    if "/flypig/" in path or "/.codebuddy/" in path:
        return None
    if name == "read_file":
        filename = path.split("/")[-1] if path else ""
        return f"📖 正在读取文件 {filename}" if filename else None
    elif name == "write_file":
        filename = path.split("/")[-1] if path else ""
        return f"✏️ 正在写入文件 {filename}" if filename else None
    elif name == "edit_file":
        filename = path.split("/")[-1] if path else ""
        return f"🔧 正在修改文件 {filename}" if filename else None
    elif name == "bash":
        return None  # bash 由前端单独处理为命令卡片
    elif name == "search_content" or name == "grep":
        pattern = args.get("pattern", "")
        return f"🔎 正在搜索 \"{pattern}\"" if pattern else None
    elif name == "find_files" or name == "search_file":
        pattern = args.get("pattern", "")
        return f"📂 正在查找文件 \"{pattern}\"" if pattern else None
```

在 SSE 事件 `tool_call` 加入 `label` 字段（None 时前端跳过）。

#### 2. 前端：`handleEvent` 改动

**`case 'llm_end'`**：

- 不再推入 messages，改为累计到 `_accumTokens`、`_accumCost`
- `thinking` 事件保持正常显示（AI 思考文字有价值）

**`case 'tool_call'`**：

- `name='bash'` → 照常推命令卡片
- `label` 存在 → 推一条 `tool-label` 消息（只显示说明文字，不可交互）
- 无 `label` → 跳过（内部文件过滤）

**`case 'tool_result'`**：

- bash 结果 → 合并到命令卡片（不变）
- 非 bash → 不显示结果（保留文件树刷新逻辑）

#### 3. 思考指示器

引入 `_hasVisibleOutput` (ref, boolean)：

- `tool_call`(bash)、`tool_call`(有 label)、`response` → 设为 true

引入 `_thinkingVisible` (ref, boolean)：

- `agentRunning` 且 `!_hasVisibleOutput` 时，延迟 500ms 设为 true
- 收到上述事件时立即设为 false

渲染：`v-if="_thinkingVisible" "🧠 AI 正在思考..."`（有淡入动画）

#### 4. 最终 token 汇总

`case 'response'` 时，如果累计 token > 0，在回复气泡末尾追加：

```html
<small class="token-summary">用了 4,827 tokens | $1.44e-05</small>
```

#### 5. 重置

`sendMessage()` 开始时重置 `_accumTokens`、`_accumCost`、`_hasVisibleOutput`、`_thinkingVisible`。