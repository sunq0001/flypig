# Hook 系统与工具链可视化

> 改进：v2：去掉 `on_tool_start`/`on_tool_end` 的硬编码判断，让 AI agent 可以动态注册通用型钩子；新增 `on_tool_chain_end` 用于工具链汇总；新增会话级累计统计。

## 一、架构

钩子系统基于**观察者模式**，`agent.py` 的 `run` 循环在关键节点调用所有已注册的钩子：

```
┌─ Agent Run Loop ──────────────────────────────────────────┐
│                                                            │
│  1. LLM 请求前    → on_lll_start(messages, iteration)      │
│                                                            │
│  2. LLM 响应后    → on_llm_end(usage, cost_info, iter)     │
│       │                                                    │
│       ├─ 无工具调用 → 直接回复用户                          │
│       │               → on_response(content)                │
│       │                                                    │
│       └─ 有工具调用 ─ 循环每个工具:                         │
│                        → on_tool_start(name, args)          │
│                        → 执行工具                           │
│                        → on_tool_end(name, result)          │
│                                                             │
│                      完成后:                                │
│                        → on_tool_chain_end(results, info)   │
│                        → 回到步骤 1                         │
│                                                             │
│  3. 最终回复        → on_response(content)                  │
└────────────────────────────────────────────────────────────┘
```

## 二、钩子接口

### `EventHook` 基类

```python
class EventHook:
    def on_llm_start(self, messages: list, iteration: int): ...
    def on_llm_end(self, usage: dict, cost_info: dict, iteration: int): ...
    def on_tool_start(self, tool_name: str, arguments: dict): ...
    def on_tool_end(self, tool_name: str, result: str): ...
    def on_tool_chain_end(self, tool_results: list, cost_info: dict, iteration: int): ...
    def on_response(self, content: str, usage_line: str): ...
```

| 方法 | 触发时机 | 关键参数 |
|------|----------|----------|
| `on_llm_start` | 每次 LLM 调用前 | `messages` — 当前对话历史, `iteration` — 当前循环轮次 |
| `on_llm_end` | LLM 响应后 | `usage` — `{input_tokens, output_tokens}`, `cost_info` — `{cost, input_cost, output_cost}` |
| `on_tool_start` | 每个工具执行前 | `tool_name` — 工具名, `arguments` — 参数 dict |
| `on_tool_end` | 每个工具执行后 | `tool_name`, `result` — 工具返回的纯文本 |
| `on_tool_chain_end` | 当前迭代所有工具执行完毕 | `tool_results` — 本轮所有结果列表, `cost_info`, `iteration` |
| `on_response` | Agent 最终回复时 | `content` — 回复文本 |
| `on_pty_output` (新增) | PTY 进程输出一行时 | `line` — 单行输出文本，用于实时流式显示 |

### 注册方式

```python
from flypig.hooks import EventHook, CostPrintHook

# 方式 1：使用默认钩子
agent = Agent(..., hooks=[CostPrintHook()])

# 方式 2：自定义钩子
class MyHook(EventHook):
    def on_tool_start(self, tool_name, arguments):
        log_to_file(f"[{tool_name}] {arguments}")

agent = Agent(..., hooks=[CostPrintHook(), MyHook()])
```

## 三、默认钩子：`CostPrintHook`

```python
class CostPrintHook(EventHook):
    def __init__(self):
        # 会话级累计
        self.session_tokens = 0
        self.session_cost = 0.0
        self.session_tools = 0
```

### 输出格式

```
[Tokens: 1,219] [Cost: $3.46e-06]        ← on_llm_end：单次 LLM token 成本
  [>] 运行命令: ls -la                     ← on_tool_start：中文说明 + 参数摘要
    hello.py                                ← on_tool_end：输出摘要（短输出全显示，长输出截取首行）
    main.py
  [Chain: 1 tools, Tokens: 1,219, Cost: $3.46e-06]  ← on_tool_chain_end：本轮汇总
[Tokens: 4,239] [Cost: $1.20e-05]         ← 下一轮 LLM
  [>] 查找文件: pattern=*.py
    ... (350 chars)                         ← 长输出只显示首行 + 字符数
  [Chain: 1 tools, Tokens: 4,239, Cost: $1.20e-05]
...
[Done] Tools: 8, Total Tokens: 35,000, Total Cost: $0.0012  ← on_response：会话累计
```

### 工具说明映射

| 工具名 | 显示中文 |
|--------|----------|
| `bash` | 运行命令 |
| `read_file` | 读取文件 |
| `write_file` | 写入文件 |
| `edit_file` | 编辑文件 |
| `find_files` | 查找文件 |
| `grep` | 搜索内容 |

### 参数摘要规则

| 工具 | 摘要内容 | 截断长度 |
|------|----------|----------|
| `bash` | 命令文本 | 90 字符 |
| `read_file`/`write_file`/`edit_file` | 文件路径 | 完整路径 |
| `find_files` | `pattern=xxx` | — |
| `grep` | 搜索模式 | 40 字符 |

### 输出摘要规则

- 输出行数 ≤ 3 且每行 < 200 字符 → 全部显示
- 否则 → 只显示首行 + `... (N chars)`

## 四、集成位置

位置在 `flypig/agent.py` 的 `run` 方法：

- **L51-53**：LLM 调用前，遍历 hooks 调 `on_llm_start`
- **L69-71**：LLM 调用后，遍历 hooks 调 `on_llm_end`
- **L84-91**：每个工具执行前后，调 `on_tool_start` / `on_tool_end`
- **L95-97**：整轮工具链执行完毕后，调 `on_tool_chain_end`
- **L115-117**：Agent 最终回复前，调 `on_response`

## 五、扩展钩子例子（待实现）

```python
class AuditLogHook(EventHook):
    """记录所有工具调用到日志文件"""
    def on_tool_start(self, tool_name, arguments):
        with open("audit.log", "a") as f:
            f.write(f"[{datetime.now()}] {tool_name} {arguments}\n")

class DebugTraceHook(EventHook):
    """打印详细的调试跟踪信息"""
    def on_llm_start(self, messages, iteration):
        print(f"[DEBUG] === Iteration {iteration} ===")
        print(f"[DEBUG] Messages: {len(messages)} items")

class TelemetryHook(EventHook):
    """发送遥测数据"""
    def on_tool_chain_end(self, tool_results, cost_info, iteration):
        requests.post("https://telemetry.example.com", json={
            "tools": len(tool_results),
            "cost": cost_info,
            "iteration": iteration,
        })
```
