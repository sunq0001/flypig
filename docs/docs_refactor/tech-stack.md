# 技术栈

> **来源**: `architecture-refactor.md` §3.12
> **关联文档**: `architecture-guide.md`（总览）、`folder-tree.md`（文件结构）
> **核心原则**：能用成熟开源的绝不自研。

## 技术选型明细

| 层次 | 模块 | 采用方案 | 类型 | 判断依据 |
|------|------|---------|------|---------|
| **前端** | UI 框架 | **Vue 3** | 市面方案 | 成熟框架，社区活跃 |
| | 流式对话 | **Vercel AI SDK (`@ai-sdk/vue`)** | 市面方案 | 一行 useChat，替代手写 ReadableStream |
| | 代码编辑器 | **Monaco Editor** | 市面方案 | VS Code 同款，语法高亮/LSP 全有 |
| | 终端模拟 | **xterm.js** | 市面方案 | 成熟终端模拟器 |
| | 图标 | **Lucide** | 市面方案 | 轻量开源图标库 |
| | 构建工具 | **Vite** | 市面方案 | 极速 HMR，原生 ESM |
| | UI 组件库 | **Element Plus** | 市面方案 | 卡片、对话框、选择题、按钮全有 |
| | 图表渲染 | **Mermaid.js** | 市面方案 | 流程图/时序图/类图，文本即图表，按需动态 import |
| | Markdown 扩展 | **marked + highlight.js** | 市面方案 | 扩展 code block 渲染器 |
| **后端** | Web 框架 | **Quart** | 市面方案 | ASGI，原生 WebSocket/SSE |
| | ASGI 服务器 | **Hypercorn** | 市面方案 | 生产级 |
| | AI 模型 SDK | **OpenAI SDK** | 市面方案 | 官方 SDK，stream=True；国产模型均兼容 OpenAI 格式 |
| | DI 容器 | **`dependency-injector`** | 市面方案 | 支持 async init、测试 override |
| | 数据库 ORM | **SQLAlchemy** | 市面方案 | 事实标准，SQLite→PostgreSQL 无缝切换 |
| | 权限策略 | **Casbin (pycasbin)** | 市面方案 | ACL/RBAC/ABAC 全支持 |
| | 对话状态机 | **LangGraph** | 市面方案 | 原生 state machine、Checkpointer、human-in-the-loop、ToolNode |
| | 沙箱 | **Docker SDK** | 市面方案 | Docker 容器隔离 |
| | 配置 | **PyYAML** | 市面方案 | yaml 解析 |
| | 代码规范检查 | **Ruff** | 市面方案 | Rust 编写，比 flake8 快 100 倍，支持 --fix 自动修复 |
| | 会话持久化 | **SQLAlchemy** | 市面方案 | 存储层用开源 ORM |
| | 历史搜索预留 | **SQLite FTS5 / PostgreSQL tsvector** | 市面方案 | IHistoryStore 接口定义，实现用数据库全文索引 |
| | CostTracker | **自研（~30 行）** | 业务定制 | 定价公式高度定制，Litellm 太重 |
| | PromptManager | **自研（~50 行）** | 业务定制 | 多角色对抗切换，无现成方案 |
| | OrchestrationService（已拆分为三） | | | 原三职合一服务拆为 GraphFactory+SuggestionEngine+HookService |
| **工具** | bash 执行 | **subprocess（标准库）** | 市面方案 | Python 内置，无 PTY |
| | 文件操作 | **Aider 编辑引擎 或 git apply** | 市面方案 | 开源方案（Aider 或标准 git apply + unified diff） |
| | 后台任务 | **subprocess.Popen + 自研 buffer** | 混合 | 标准库执行 + 自研环形缓冲区 |
| | 代码规范检查 | **Ruff CLI** | 市面方案 | subprocess 调用 ruff --fix，自动修复 |
| | 文件上传 | **Element Plus Upload** | 市面方案 | 前端拖拽，后端接收解压 |
| | 压缩解压 | **zipfile/tarfile/py7zr** | 市面方案 | 标准库 + py7zr，含 Zip Slip 防护 |
| | **断路器** | **自研 @circuit_breaker** | 业务定制 | 调用连续失败 5 次自动熔断 60s |
| | **重试机制** | **自研 async retry** | 业务定制 | 网络抖动自动重试，指数退避 |
| | **监控** | **prometheus_client** | 市面方案 | Counter/Histogram/Gauge，暴露 /metrics |
| | 选择题卡片 | **自研 tool_ask_choice** | 业务定制 | 核心 UX 模式，~20 行返回值 |
| | MCP 协议 | **社区标准（mcp.json）** | 市面方案 | 不自研协议；[v1] 提示用户手动安装 |
| | 工具路由 | **LangGraph ToolNode** | 市面方案 | 标准 LangGraph tool node |
| **DevOps** | 容器编排 | **Docker Compose** | 市面方案 | 单机足够 |
| | 反向代理 | **Nginx** | 市面方案 | 静态文件+SSL |

## 总结

- **开源方案 ~94%** — LangGraph + Casbin + dependency-injector + Element Plus + Mermaid.js + Vercel AI SDK + Ruff + Quart + SQLAlchemy + marked + highlight.js + Docker...
- **真正自研 ~4%** — PromptManager(~50行)、CostTracker(~30行)、GraphFactory(~80行)+SuggestionEngine(~40行)+HookService(~40行)、ChangeScore(~40行)、ChangeReview(~60行)
- **薄包装不计入** — tool_ask_choice(~20行)、tool_lint(~20行调Ruff)、IHistoryStore(接口定义)
