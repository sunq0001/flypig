---
name: architecture-redesign-doc
overview: 根据用户指出的核心问题(前端没有对流式输出进行适配、AI操作应使用subprocess、简化终端交互模型)，更新架构设计文档 terminal-interaction-v8.md
todos:
  - id: cleanup-pty
    content: 删除所有 PTY/交互式/terminal_inject 相关遗留代码（tools.py, server.py, index.html, terminal.py）
    status: completed
  - id: add-stream-method
    content: ModelAdapter 添加 chat_stream() 流式方法，使用 OpenAI SDK stream=True 逐 token yield
    status: completed
  - id: refactor-agent-stream
    content: Agent.run() 改为流式输出模式，逐 token 调用 on_response_token 钩子
    status: completed
    dependencies:
      - add-stream-method
  - id: refactor-sse-server
    content: 重写 server.py /api/chat SSE 为逐 token 推流，添加 token/response_end 事件类型
    status: completed
    dependencies:
      - cleanup-pty
      - refactor-agent-stream
  - id: refactor-frontend-stream
    content: 重写前端 SSE 消费为真流式渲染（ReadableStream 逐 token 追加），删除所有模拟打字/PTY 注入代码
    status: completed
    dependencies:
      - refactor-sse-server
  - id: simplify-subprocess
    content: 简化 _run_subprocess_async_core 为直接 communicate()，添加 task_log(pid) 后台进程管理工具
    status: completed
    dependencies:
      - cleanup-pty
  - id: update-docs
    content: 更新 roadmap.md 和 terminal-interaction 文档为新架构说明
    status: completed
    dependencies:
      - cleanup-pty
      - refactor-subprocess
      - refactor-sse-server
      - refactor-frontend-stream
---

## 需求说明

基于目前项目的混乱状态和用户的要求，需要重新设计架构：

### 核心痛点

1. **前端流式输出是假的**：`_startStreaming` 用 setInterval 模拟打字，体验差且阻塞输入框
2. **PTY 注入链路过于复杂**：AI→SSE→前端→API→后端→PTY 共 7 步，从未稳定工作
3. **交互式/耗时/普通命令边界混乱**：多个版本的检测逻辑互相覆盖

### 重新设计方案

参照 CodeBuddy、Claude Code 等成熟项目的做法：

1. **真流式响应**：后端逐 token 推送 AI 回复（OpenAI SDK stream=True），前端 ReadableStream 实时渲染
2. **subprocess 替代 PTY**：所有命令走 subprocess，快速命令 `subprocess.run()`，长任务 `subprocess.Popen()` 后台运行
3. **完全去除 PTY**：删除 `_run_terminal_interactive`、`terminal_inject`、独立 SSE 端点、xterm.js WebSocket 桥接等全部相关代码
4. **终端面板改为只读输出查看器**：展示 subprocess 执行记录的只读视图，不涉及交互
5. **交互式命令**：完全交给用户自己，AI 不再管理

### 涉及改动

- 后端：ModelAdapter 添加流式、Agent 改为流式输出、/api/chat SSE 推流
- 前端：ReadableStream 逐 token 消费、重写 response 渲染逻辑
- 删除：PTY 注入、终端事件、交互式检测等遗留代码
- 简化：subprocess 执行逻辑（移除 2s/3s 超时脆弱逻辑）
- 新增：后台进程管理工具 task_log(pid)

## 技术方案

### 技术栈

- 后端：Python + Quart (现有，保留 ASGI 架构)
- AI 模型：OpenAI SDK (stream=True 模式支持真流式)
- 前端：Vue 3 + 原生 ReadableStream (SSE 逐 token 解析)
- 命令执行：asyncio.create_subprocess_shell / subprocess.Popen

### 架构设计

**新数据流（简化为 4 步）**：

```mermaid
flowchart LR
    A[用户输入] --> B[/api/chat SSE]
    B --> C[Agent 流式执行]
    C --> D[逐 token 推流]
    C --> E[工具调用]
    E --> F[subprocess 执行]
    F --> G[返回结果]
    G --> C
    D --> H[前端 ReadableStream]
    H --> I[逐字渲染]
```

**相比旧架构的变化**：

- 删除：PTY WebSocket 通道、独立终端 SSE 端点、inject-bind API、终端注入绑定逻辑
- 删除：_run_terminal_interactive、_guess_interactive、wrapped_command、###AI_START/END### 标记
- 删除：_silence_check 独立任务、_terminal_injections 全局状态
- 简化：_run_subprocess_async_core 改为直接 communicate()
- 新增：chat_stream() 流式方法、on_response_token 钩子、task_log 工具

### 关键设计决策

**1. 流式方案：原生 SSE token 流（不引入 Vercel AI SDK）**

Vercel AI SDK 主要绑定 Next.js/React 生态，我们的项目使用 Vue 3 + Python Quart，引入 SDK 会带来不必要的依赖和适配成本。使用原生 SSE 协议 + ReadableStream 更轻量，且能精确控制事件格式。

事件格式变更（/api/chat SSE）：

```
当前: data: {"type":"response","content":"完整回复文字..."}
改为:
data: {"type":"token","content":"每"}
data: {"type":"token","content":"个"}
data: {"type":"token","content":"token"}
data: {"type":"token","content":"单独"}
data: {"type":"token","content":"推送"}
data: {"type":"response_end","usage":{...}}
```

前端消费方式：

```javascript
// fetch + ReadableStream 逐行解析 SSE
const reader = res.body.getReader();
while (true) {
  const {done, value} = await reader.read();
  // 解析 lines，遇到 type:token 就追加到当前 message
  // 遇到 type:response_end 就结束
}
```

**2. subprocess 策略**

- **快速命令**（pip install, git, ls）：`asyncio.create_subprocess_shell` + `proc.communicate()`，同步等待完整输出。超时设为 timeout_val（默认30s）。
- **后台长任务**（服务器启动）：`subprocess.Popen(stdout=PIPE, stderr=PIPE)`，返回 PID。AI 可通过 `task_log(pid)` 工具获取 stdout/stderr 的已缓存内容。
- **交互式命令**：AI 检测到脚本含 `input()` 时，返回提示 "此命令需要交互式终端，请手动运行"。

**3. 删除 PTY 的全部理由**

- pywinpty 阻塞读问题无法根本解决（静默检测+独立任务只是补丁）
- PowerShell 不兼容 `&&` 等 bash 语法
- 7 步注入链路延迟不可控
- CodeBuddy/Claude Code 都不用 PTY，用 subprocess 安全可靠
- xterm.js + WebSocket 桥接复杂度过高，收益低

**4. 终端面板的新定位**

从"AI 管理的交互式终端"改为"用户手动操作的独立终端 + 只读执行记录面板"：

- 独立的 xterm.js 终端（保留给用户手动使用，AI 不注入命令）
- 新增只读的"命令执行记录"面板，展示所有 subprocess 执行的命令和输出
- AI 不再有"聚焦终端"、"终端注入"等能力

### 目录结构变化

```
flypig/
├── tools.py              # [MODIFY] 删除 PTY 相关方法，简化 subprocess，添加 task_log
├── agent.py              # [MODIFY] 改为流式输出，添加 on_response_token 钩子
├── model.py              # [MODIFY] 添加 chat_stream() 流式方法
├── web/
│   ├── server.py         # [MODIFY] 删除 PTY 端点，重写 /api/chat SSE
│   ├── terminal.py       # [DELETE] PTY 管理不再需要
│   └── static/
│       └── index.html    # [MODIFY] 重写 SSE 消费为真流式，删除 PTY 注入逻辑
docs/
├── roadmap.md            # [MODIFY] 更新路线图
└── terminal-interaction-v7.md  # [MODIFY] 更新为新架构描述
```

### 实施要点

1. **先读后删**：删除大量遗留代码前，先确认没有引用依赖链
2. **ModelAdapter 向后兼容**：chat_stream() 作为新方法，保留 chat() 备用
3. **Agent 迭代逻辑不变**：工具调用、重复检测、自愈等逻辑不变，只是输出方式改为流式
4. **前端逐 token 渲染防 XSS**：token 内容用 textContent 设置，不直接用 innerHTML
5. **后台进程清理**：subprocess.Popen 的任务在 agent reset 或超时后自动 kill

### 修改文件清单

| 文件 | 改动内容 |
| --- | --- |
| `flypig/model.py` | 新增 `chat_stream()` 方法，使用 `stream=True` 逐 token yield |
| `flypig/agent.py` | `run()` 方法新增 `chat_stream()` 路径，逐 token 调用钩子；添加 `on_response_token` 钩子 |
| `flypig/web/server.py` | SSE 事件添加 `token` 类型；删除 `/api/terminal-events`、`/api/terminal/output/<msg_id>`、`/api/terminal/inject-bind/<msg_id>`；删除 `_terminal_injections`、`_active_injections`、`_SILENCE_THRESHOLD`、`_extract_output_between_markers`、`_silence_check` 等 |
| `flypig/tools.py` | 删除 `_run_terminal_interactive()`、`_guess_interactive()`、`wrapped_command`、`_INTERACTIVE_COMMANDS` 集合；简化 `_run_subprocess_async_core()` 为直接 `communicate()`；添加 `task_log(pid)` 工具 |
| `flypig/web/terminal.py` | 废弃整个文件（PTY 管理、TerminalManager 等不再需要） |
| `flypig/web/static/index.html` | 删除 `terminal_inject` case、`_doInject`、`_injectCommandToActiveTerminal`、`_waitAndInject`、`_connectTerminalEvents`、`handlePushResult`、`_autoPushTerminalResult`；重写 `case 'response'` 为逐 token 追加；添加 `case 'response_end'`；重写 SSE 消费循环 |
| `docs/roadmap.md` | 更新 Web UI 交互部分，标记 PTY 相关为已移除 |
| `docs/terminal-interaction-v7.md` | 用新架构说明替换旧内容 |