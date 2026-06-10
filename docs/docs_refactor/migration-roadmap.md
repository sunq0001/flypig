# 迁移路线

> **来源**: `architecture-refactor.md` §6, §10
> **关联文档**: 所有子文档（执行到对应 Step 时参考对应文档）
> 改迁移顺序或 MVP 范围时，需同步检查所有子文档的依赖关系。

> 总原则：先拆后改，不破坏现有功能。每种新增模块按先后顺序逐步引入。

## Step 1：LangGraph + 接口定义 + 核心工具

| 动作 | 说明 |
|------|------|
| 安装 langgraph, langchain-core, langchain-openai | 新增依赖 |
| 定义 LangGraph StateSchema + 接口（IModel, IToolExecutor 等） | 只加新文件 |
| 配置 dependency-injector 容器（含 IConversationStore + IContextPipeline） | 新文件 |
| 创建 `domain/interfaces/iconversation_store.py`（IConversationStore 接口 + NoOp） | 新文件 |
| 创建 `domain/interfaces/icontext_pipeline.py`（IContextPipeline 接口 + 默认实现） | 新文件 |

## Step 2：工具拆包 + 注册到 ToolNode

| 动作 | 说明 |
|------|------|
| 创建 `infrastructure/tools/` 包 | 只加新文件 |
| 迁入：tool_bash.py, tool_file.py, tool_search.py, tool_task.py | 拆分 |
| 迁入：tool_ask_choice.py, tool_extract_archive.py | 新文件 |
| 迁入：tool_change_review.py, tool_lint.py, tool_change_score.py | 新文件 |
| 迁入：tool_mcp_manager.py + mcp_loader.py | 新文件 |
| 注册全部工具到 LangGraph ToolNode | 新代码 |

## Step 3：Web 层重组

| 动作 | 说明 |
|------|------|
| 创建 `interface/web/routes/` 路由包 | 只加新文件 |
| 拆分 server.py 路由到 routes/chat.py, config.py, files.py 等 | 保留旧文件做兼容 |

## Step 4：LangGraph + 终端重构 + 对抗审查

| 动作 | 说明 |
|------|------|
| 用 LangGraph 定义统一 StateGraph + 条件路由（替换旧 Agent.run） | 核心替换 |
| 实现 `domain/agent/state.py`（AgentState） + `application/services/graph_factory.py`（图构建） | 新文件 |
| 实现 suggestion_node + handle_adversarial_decision | 新节点 |
| 扩展 AgentState：change_review, rejected_changes, change_score 等 | 扩展 |
| 删除 PTY 注入全部代码 | 清理 |
| **重写** terminal.py（仅保留用户手动 PTY 的 WebSocket 管理） | 大幅精简 |
| 注册 graph_factory.py + suggestion_engine.py + hook_service.py 到 DI 容器 | 新服务 |

## Step 5：前端 Vite 迁移 + Vercel AI SDK + 富内容组件

| 动作 | 说明 |
|------|------|
| 安装 Vercel AI SDK, Element Plus, mermaid, marked, highlight.js | 新增依赖 |
| 用 useChat 替换手写 SSE | 删除 ~200 行 |
| 拆 index.html 成 20+ .vue 组件 | 并行开发 |
| 创建：ChangeReviewCard, SuggestionCard, MermaidDiagram, LivePreview, ChoiceCard | 新组件 |
| 扩展 composables/useMarkdownRender.js（检测 mermaid/html/vue 代码块） | 扩展 |

## Step 6：Docker Compose 容器化

| 动作 | 说明 |
|------|------|
| 创建 Dockerfile, docker-compose.yml | 只加新文件 |

## Step 7：清理 + 验证

| 动作 | 说明 |
|------|------|
| 删除旧大文件（tools.py, server.py, sandbox.py, terminal.py 旧版） | 最终清理 |
| 回归测试：所有模式（Explore/Plan/Execute）的对话流 | 功能验证 |
| 回归测试：变更审查 → LINT → 对抗建议 → 用户选择 → 审批 | 流程验证 |

## MVP 迭代建议

| 轮次 | 目标 | Steps | 可演示功能 | 不做 |
|------|------|-------|-----------|------|
| 第 1 轮 | 基础骨架 | 1-4 裁剪 | 单图 LLM 对话 + 工具调用 | 模式区分、审查、lint、Mermaid |
| 第 2 轮 | 前端+流式 | 5+3 | 完整前端 + useChat + 卡片渲染 | — |
| 第 3 轮 | 高级特性 | 4 补齐+6-7 | Lint、对抗建议、Mermaid、MCP | — |

## 第 1 轮不做的功能

| 功能 | 原因 |
|------|------|
| 模式区分（Explore/Plan/Execute） | 先不区分，LLM 直接对话+调工具 |
| 变更审查（ChangeReview） | 先不做卡片，用户直接看 diff |
| Lint 自动修复 | 先不集成 ruff |
| 对抗建议（SuggestionCard） | 先不做评分 |
| 富内容图表（Mermaid/LivePreview） | 先只支持文本和 Markdown |
| MCP 集成 | 先不装任何 MCP 服务器 |

## DevOps 架构

> **详见独立文档 `operations.md`**：Docker Compose 配置、CI/CD 流水线、环境变量、健康检查、SaaS 扩展。
