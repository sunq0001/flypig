# 迁移路线

> **来源**: `architecture-refactor.md` §6, §10
> **关联文档**: 所有子文档（执行到对应 Step 时参考对应文档）
> 改迁移顺序或 MVP 范围时，需同步检查所有子文档的依赖关系。

> **总原则**：重写而非重构。旧 `flypig/` 整体归档为 `archive/flypig/`，新代码从零搭建，不依赖任何旧文件。

---

## 第 0 轮：地基搭建（基础设施 + 骨架）

| Step | 名称 | 说明 |
|------|------|------|
| **Step -2** | 旧代码归档 | `flypig/` 全部移入 `archive/flypig/`，只保留 `.gitkeep` 占位 |
| **Step -1** | 建空骨架 | 按 `folder-tree.md` 创建目录 + 所有 `__init__.py` + 空文件 |
| **Step 0** | 开发者工具链 | MkDocs + mkdocstrings、Ruff D、interrogate、pre-commit |

### Step -2：旧代码归档

| 动作 | 说明 |
|------|------|
| 创建 `archive/` 目录 | 存放旧版 FlyPig 代码 |
| 移动 `flypig/` → `archive/flypig/` | 全部文件（含前端和后台） |
| 验证：`archive/flypig/` 结构完整 | 确保未遗漏文件，日后可回溯 |
| 在 `flypig/` 根目录留 `.gitkeep` | 避免空目录提交丢失 |

### Step -1：建空骨架

| 动作 | 说明 |
|------|------|
| 对照 `folder-tree.md` 创建所有目录 | `flypig/core/`, `flypig/domain/`, `flypig/orchestration/` … 共约 30+ 个子目录 |
| 在每个目录创建 `__init__.py` | 保证 Python 包可导入 |
| 创建所有空 `.py` 文件 | 每个文件顶部写模块 docstring 骨架（`"""... TODO: implement"""`） |
| 创建根级配置文件 | `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `nginx.conf`, `mcp.json`, `.env.example`, `Makefile` |
| 新建 `tests/` 目录 | 含 `conftest.py`, `pytest.ini`, `unit/`, `integration/`, `fixtures/` |
| 新建 `frontend/` 骨架 | `frontend/static/` + `frontend/static_vite/` 含 `package.json`, `vite.config.js`, `index.html`, `src/main.js` |
| 新建 `scripts/` 目录 | `setup_env.py`（核心）+ `setup_env.bat` + `setup_env.sh`（入口）, `seed_data.py`, `migrate_db.py` |
| 验证：`python -c "import flypig"` | 确保包结构可导入，不报错 |

### Step 0：开发者工具链搭建

| 动作 | 说明 |
|------|------|
| 安装 MkDocs + mkdocstrings | `pip install mkdocs mkdocstrings[python]` — 文档站框架，自动从 docstring 拉取 API 文档 |
| 初始化 MkDocs 配置 | `mkdocs new .` 后编辑 `mkdocs.yml`，nav 包含所有 `docs_refactor/*.md` + python 插件源 |
| 配置 Ruff D 规则 | `pyproject.toml` 中 `[tool.ruff.lint] select = ["D"]` + `convention = "google"` — 强制 Google 风格 docstring |
| 安装 interrogate | `pip install interrogate`，配置 `[tool.interrogate] fail-under = 80` — docstring 覆盖率门槛 ≥80% |
| 安装 pre-commit | `pip install pre-commit` + `pre-commit install`，创建 `.pre-commit-config.yaml` 含 ruff D + interrogate 钩子 |
| 验证工具链 | `ruff check flypig/` → 无 D 规则报错；`interrogate flypig/` → 覆盖率通过 |

---

## 第 1 轮：后端核心（LangGraph + DI + 接口）

| Step | 名称 | 说明 |
|------|------|------|
| **Step 1** | 领域层 + DI 容器 | 定义所有接口、数据模型、AgentState、DI 容器 |
| **Step 2** | 工具系统 | 从零写全部工具，注册到 ToolNode |
| **Step 3** | LangGraph 图 | 写 graph_factory、nodes、router、ChatService |

### Step 1：领域层 + DI 容器

| 动作 | 说明 |
|------|------|
| 安装 langgraph, langchain-core, langchain-openai | 新增依赖 |
| 定义 `domain/interfaces/` 全部接口（IModel, IToolExecutor, IConversationStore, IContextPipeline, IHook, IAgent, IUsageTracker, ILicenseService, IUpdateService） | 新写，含 Google 风格 docstring |
| 定义 `domain/models/` 全部数据类（Message, Session, Mode, ChangeScore, Task） | 新写 |
| 定义 `domain/agent/state.py`（AgentState TypedDict） | 新写 |
| 定义 `domain/exceptions.py`（统一异常体系） | 新写 |
| 定义 `domain/config/config.py` + `domain/config/model_registry.py` | 新写 |
| 编写 `domain/prompts/multirole_manager.py` + `domain/prompts/` 5 份 prompt | 新写 |
| 配置 `di/container.py`（dependency-injector，注册所有接口和实现） | 新写 |
| 验证：`pytest --collect-only` 通过 | 包结构完整 |

### Step 2：工具系统

| 动作 | 说明 |
|------|------|
| 创建 `infrastructure/tools/` 包 | 所有工具从零新写 |
| 写 `executor.py`（ToolExecutor 调度器） | 核心调度逻辑 |
| 写 `file/` 一组：tool_read.py, tool_write.py, tool_patch_file.py, tool_delete.py, tool_list_dir.py + `review/` 一组：tool_change_review.py, tool_lint.py, tool_change_score.py | 代码编辑+审查工具链 |
| 写 `search/` 一组：tool_search.py, tool_web_search.py, tool_ask_choice.py | 搜索/调研工具 |
| 写 `system/` 一组：tool_bash.py, tool_git.py, tool_fetch_url.py, tool_list_dir.py, tool_datetime.py, tool_calc.py, tool_task.py, tool_task_manager.py, tool_ocr.py, tool_extract_archive.py | 系统工具 |
| 写 `mcp/` 一组：tool_mcp_loader.py, tool_mcp_manager.py | MCP 协议工具 |
| 写 `tools/utils.py` | 公共工具函数 |
| 注册全部工具到 LangGraph ToolNode | 在 container.py 中串联 |

### Step 3：LangGraph 图 + 对话编排

| 动作 | 说明 |
|------|------|
| 写 `domain/agent/nodes.py`（chat/ask_choice/execute/lint/review/suggest 节点函数） | 新写 |
| 写 `domain/agent/router.py`（条件边路由逻辑） | 新写 |
| 写 `domain/agent/context.py`（Explore/Plan/Execute context 约束） | 新写 |
| 写 `orchestration/graph_factory.py`（组装 nodes + router → 编译 StateGraph） | 新写 |
| 写 `orchestration/chat_service.py`（对话编排主服务） | 新写 |
| 写 `orchestration/event_subscriptions.py`（事件订阅编排） | 新写 |
| 写 `orchestration/suggestion_engine.py`（评分→建议映射） | 新写 |
| 写 `orchestration/context_pipeline.py`（上下文压缩） | 新写 |
| 写 `orchestration/git_checkpoint_manager.py`（Agent Git checkpoint） | 新写 |
| 写 `orchestration/conversation_store.py`（SQLite 实现） | 新写 |
| 写 `orchestration/summary_generator.py`（短语摘要） | 新写 |
| 写 `orchestration/session_service.py` + `config_service.py` + `policy_service.py` | 新写 |
| 写 `infrastructure/hooks.py`（钩子实现） + `process_manager.py`（后台任务） | 新写 |
| 验证：可运行单轮对话（SSE 事件流输出） | 功能验证 |

---

## 第 2 轮：接口层 + 基础设施

| Step | 名称 | 说明 |
|------|------|------|
| **Step 4** | Web 层 | FastAPI 路由 + SSE 队列 |
| **Step 5** | 基础设施 | 模型适配、终端、沙箱、权限、用量追踪 |

### Step 4：Web 层

| 动作 | 说明 |
|------|------|
| 写 `backend/server.py`（app 声明 + 路由注册） | 新写 |
| 写 `backend/routes/` 全部路由（chat.py, config.py, files.py, sessions.py, health.py, upload.py, rollback.py, agent_routes.py, history.py, usage.py, tasks.py, feedback.py） | 新写 |
| 写 `backend/sse_queue.py` + `backend/file_watcher.py` | 新写 |
| 写 `__main__.py`（接口选择 + DI 初始化 + 启动） | 入口点 |

### Step 5：基础设施

| 动作 | 说明 |
|------|------|
| 写 `infrastructure/llm/`（openai_adapter.py, anthropic.py, local.py） | 模型适配 |
| 写 `infrastructure/sandbox/`（Docker 沙箱配置、路径验证、生命周期、镜像构建） | 新写 |
| 写 `infrastructure/terminal.py`（精简版，仅用户手动 PTY WebSocket，无 AI 注入） | 新写 |
| 写 `infrastructure/policies/permission_checker.py`（file/term/git/test, allow/ask/deny） | 新写 |
| 写 `infrastructure/policies/`（Casbin 初始化配置） | 新写 |
| 写 `infrastructure/usage/`（sqlite_tracker.py, pricing.py, usage_handler.py） | 用量追踪 |

---

## 第 3 轮：前端

| Step | 名称 | 说明 |
|------|------|------|
| **Step 6** | 前端 Vite + Vue | 从零搭建 Vite + Vue + Element Plus |

### Step 6：前端 Vite + Vue

| 动作 | 说明 |
|------|------|
| 初始化 `frontend/static_vite/`（package.json, vite.config.js, index.html） | 新写 |
| 安装 Vercel AI SDK, Element Plus, mermaid, marked, highlight.js | 新增依赖 |
| 写 `src/main.js` + `src/App.vue`（三栏布局 + 终端面板） | 新写 |
| 写 `src/style/`（5 个 CSS 文件：变量、终端主题 ×2、base） | 新写 |
| 写 `src/components/layout/`（MainLayout, ResizeHandle, StatusBar） | 新写 |
| 写 `src/components/sidebar/`（Sidebar, FileTree, FileTreeNode, Dashboard, TaskBoard） | 新写 |
| 写 `src/components/editor/`（EditorArea, EditorTabs, MonacoEditor） | 新写 |
| 写 `src/components/chat/`（ChatPanel, MessageList, InputBox, ChoiceCard, ChangeReviewCard, SuggestionCard, MermaidDiagram, LivePreview, MessageItem, ThinkingIndicator, ToolCallCard, TaskListCard, FilePreview, ImagePreview） | 新写 |
| 写 `src/components/terminal/`（TerminalPanel, TerminalTab, XtermViewer, OutputViewer） | 新写 |
| 写 `src/components/init/`（InitWizard, WorkspaceStep, ModelStep, ApiKeyStep） | 新写 |
| 写 `src/components/common/`（MarkdownRender, CodeBlock, LoadingSpinner, ThemeSwitcher, CommandPalette, TaskHistoryDialog, RecoveryDialog） | 新写 |
| 写 `src/composables/`（useChat, useMessages, useTerminal, useFileTree, useEditor, useLayout, useMarkdownRender, useTheme, useCommandPalette, useTasks, useDraft, useFileDrop） | 新写 |
| 写 `src/lib/`（xterm-setup.js, monaco-setup.js, sfc-compiler.js） | 新写 |
| 用 useChat 连接后端 SSE | 前后端联调 |

---

## 第 4 轮：容器化 + 验证

| Step | 名称 | 说明 |
|------|------|------|
| **Step 7** | Docker Compose | 容器化部署 |
| **Step 8** | 清理 + 验证 | 全流程回归 |

### Step 7：Docker Compose 容器化

| 动作 | 说明 |
|------|------|
| 创建 `Dockerfile` | 应用容器化 |
| 创建 `docker-compose.yml` | api + nginx 编排 |
| 创建 `nginx.conf` | 反向代理 + 静态文件 + SSL |
| 验证：`docker compose up` 正常启动 | 可访问 Web UI |

### Step 8：清理 + 验证

| 动作 | 说明 |
|------|------|
| 跑 interrogate 验证 docstring 覆盖率 ≥ 80% | 规范验证 |
| `mkdocs build` 验证文档站可正常构建 | 文档验证 |
| 全链路测试：所有模式（Explore/Plan/Execute）的对话流 | 功能验证 |
| 全链路测试：变更审查 → LINT → 对抗建议 → 用户选择 → 审批 | 流程验证 |
| 全链路测试：MCP 工具加载 + 调用 | 扩展验证 |
| 性能回归：启动时间、首次对话延迟、工具调用耗时 | 非功能验证 |

---

## 物理文件映射（完整目标清单）

| 层次 | 文件数 | 分布 |
|------|--------|------|
| 领域层 `domain/` | ~25 个 `.py` | 接口、模型、agent、prompts、policies、config |
| 编排层 `orchestration/` | ~12 个 `.py` | 服务 |
| 基础设施层 `infrastructure/` | ~30 个 `.py` | 模型适配、工具（~20）、沙箱、终端、用量、权限、Casbin |
| 后端层 `backend/` | ~15 个 `.py` | 路由（11）、服务（2）、server、terminal、main |
| 前端 `frontend/` | ~45 个文件 | 组件（~30）、composables（12）、lib（3）、style（5）、配置 |
| 根级配置 | ~8 个文件 | pyproject.toml, Dockerfile, docker-compose.yml, nginx.conf, mcp.json, model.conf, policy.csv |
| 测试 `tests/` | ~12 个 `.py` | unit（5）、integration（3）、fixtures、conftest、pytest.ini |
| **合计** | **~150 个文件** | |

---

## MVP 迭代建议

| 轮次 | 目标 | Steps | 可演示功能 | 不做 |
|------|------|-------|-----------|------|
| **MVP 1** | 骨架 + 后端核心 | -2 → 3 | 单图 LLM 对话 + 工具调用 + SSE 输出 | 模式区分、审查、lint、前端、沙箱 |
| **MVP 2** | 接口 + 前端 | 4 → 6 | 完整 Web UI + useChat 流式渲染 + 文件管理 | Mermaid、对抗建议、Docker |
| **MVP 3** | 高级特性 | 7 → 8 | Lint、对抗建议、MCP、Mermaid、Docker | — |

## MVP 1 不做的功能

| 功能 | 原因 |
|------|------|
| 模式区分（Explore/Plan/Execute） | 先不区分，LLM 直接对话+调工具 |
| 变更审查（ChangeReview） | 先不做卡片，用户直接看 diff |
| Lint 自动修复 | 先不集成 ruff |
| 对抗建议（SuggestionCard） | 先不做评分 |
| 富内容图表（Mermaid/LivePreview） | 先只支持文本和 Markdown |
| MCP 集成 | 先不装任何 MCP 服务器 |
| 前端 Web UI | MVP 1 仅用 curl/wscat 测试 SSE |
| Docker 沙箱 | MVP 1 仅本机 subprocess |

## MVP 2 不做的功能

| 功能 | 原因 |
|------|------|
| Mermaid 渲染 | 第 3 轮做 |
| 对抗建议卡片 | 第 3 轮做 |
| Docker Compose | 第 4 轮做 |

## DevOps 架构

> **详见独立文档 `operations.md`**：Docker Compose 配置、CI/CD 流水线、环境变量、健康检查、SaaS 扩展。
