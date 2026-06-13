# 项目文件夹树（统一标准）

> **来源**: 全文档提取（`architecture-refactor.md` §3.1-§10）
> **关联文档**: `architecture-guide.md`（总览）、`backend-modules.md`（模块职责）、`usage-tracking.md`（usage/ 模块）
> **本树是唯一标准**，所有内联文件夹树以此为准。改结构时只需改这里，其他地方删掉冗余树。

---

## 目标文件夹树

```
flypig/
│
├── __main__.py                   ← 入口点（DI 初始化 + 启动）
│
├── core/                         ← 应用骨架（胶水代码）
│   ├── __init__.py
│   ├── config.py                 ← 配置加载（从 YAML/环境变量）
│   ├── container.py              ← dependency-injector 配置
│   ├── logging.py                ← Loguru 初始化
│   ├── events.py                 ← 启动/关闭事件
│   └── app.py                    ← Quart app 工厂
│
├── domain/                       ← 领域层（零外部依赖）
│   ├── __init__.py
│   ├── interfaces/               ← 抽象接口
│   │   ├── imodel.py             ← IModel（context 驱动，统一 stream 接口）
│   │   ├── itool_executor.py     ← IToolExecutor（含 MCP 动态注册）
│   │   ├── iknowledge_store.py   ← IKnowledgeStore（NoOp 预留）
│   │   ├── iconversation_store.py  ← IConversationStore（对话存储 + 检索）
│   │   ├── icontext_pipeline.py   ← IContextPipeline（预 LLM 压缩）
│   │   ├── iusage_tracker.py     ← IUsageTracker（用量追踪接口）
│   │   ├── ilicense_service.py   ← ☆ P2 许可激活接口（NoOp 预留）
│   │   ├── iupdate_service.py    ← ☆ P2 自动更新接口（NoOp 预留）
│   │   ├── ihook.py              ← IHook（事件钩子）
│   │   └── iagent.py             ← IAgent
│   │
│   ├── agent/                    ← LangGraph（领域层只定义节点和状态）
│   │   ├── state.py              ← AgentState TypedDict（纯数据，零依赖）
│   │   ├── nodes.py              ← 节点函数（chat/ask_choice/execute/lint/review/suggest）
│   │   ├── router.py             ← 条件边路由逻辑（基于 tool_calls）
│   │   └── context.py            ← Explore/Plan/Execute context 约束
│   │
│   ├── models/                   ← 数据类
│   │   ├── message.py            ← Message, ToolCall, ChoiceCard
│   │   ├── session.py            ← Session
│   │   ├── mode.py               ← ExecutionMode 枚举 + ModeConfig
│   │   ├── change_score.py       ← ChangeScore（§3.8.9）
│   │   └── task.py               ← TaskItem / TaskStatusChange / TaskStats
│   │
│   ├── prompt_manager.py         ← 多角色 prompt 切换
│   ├── prompts/                  ← prompt 仓库
│   │   ├── developer.md          ← 核心开发者身份
│   │   ├── reviewer.md           ← 代码审查员（对抗性）
│   │   ├── tester.md             ← 测试员
│   │   ├── architect.md          ← 重构/架构评估
│   │   └── documenter.md         ← 文档撰写
│   │
│   ├── config/                   ← 配置数据类（纯数据，无 IO）
│   │   ├── config.py             ← Config dataclass
│   │   └── model_registry.py     ← ModelRegistry dataclass
│   └── exceptions.py             ← 统一异常
│
├── application/                  ← 应用层
│   ├── services/
│   │   ├── chat_service.py       ← 对话编排：调用 LangGraph → 事件分发
│   │   ├── config_service.py     ← 配置管理
│   │   ├── session_service.py    ← 会话状态管理
│   │   ├── policy_service.py     ← Casbin 封装
│   │   ├── graph_factory.py      ← ★ 图构建：组装 nodes + router → 编译 StateGraph
│   │   ├── suggestion_engine.py  ← ★ 评分→建议映射：generate_suggestion()
│   │   ├── hook_service.py       ← ★ 钩子管理器：register / emit
│   │   ├── git_checkpoint_manager.py ← ★ Agent Git checkpoint 管理
│   │   ├── context_pipeline.py    ← ★ 预 LLM 上下文压缩（Truncate+Trim+Fold）
│   │   ├── conversation_store.py  ← ★ 对话存储 SQLite（IConversationStore 实现）
│   │   ├── usage_tracker_service.py  ← ★ 用量追踪编排（IUsageTracker + PricingFetcher）
│   │   ├── export_service.py     ← ☆ P1 导入/导出服务（NotImplemented 预留）
│   │   ├── model_fallback_service.py ← ☆ P1 多模型 fallback（P0 仅记录）
│   │   └── summary_generator.py  ← ★ 自动生成短语摘要
│   └── dto/
│       ├── chat_dto.py           ← 数据传输对象
│       └── config_dto.py
│
├── infrastructure/               ← 基础设施层
│   ├── model/                    ← 模型适配
│   │   ├── openai_adapter.py     ← OpenAI/DeepSeek 兼容（国产主力）
│   │   ├── anthropic.py          ← Claude 适配
│   │   └── local.py              ← 本地模型（Ollama/vLLM, 预留）
│   │
│   ├── tools/                    ← 工具执行（按功能分组）
│   │   ├── __init__.py
│   │   ├── executor.py           ← ToolExecutor 主类（调度器）
│   │   ├── edit/                 ← 代码编辑工具
│   │   │   ├── tool_file.py          ← read/write/edit（Aider 或 git apply）
│   │   │   ├── tool_change_review.py ← 变更审查数据生成（§3.8.7）
│   │   │   ├── tool_lint.py          ← 代码规范自动检查（Ruff, §3.8.8）
│   │   │   └── tool_change_score.py  ← 变更影响评分（§3.8.9）
│   │   ├── search/               ← 搜索调研工具
│   │   │   ├── tool_search.py        ← grep + find_files
│   │   │   ├── tool_web_search.py    ← ☆ P1 内置网络搜索（DuckDuckGo）
│   │   │   └── tool_ask_choice.py    ← Explore 选择题（§3.6.3）
│   │   ├── system/               ← 系统工具
│   │   │   ├── tool_bash.py          ← subprocess 命令（无 PTY）
│   │   │   ├── tool_git.py           ← ★ Git 操作代替裸 bash：status/diff/log/commit/branch
│   │   │   ├── tool_fetch_url.py     ← ★ 网页抓取（httpx，零依赖）
│   │   │   ├── tool_project_scan.py  ← ★ 项目扫描：树结构/语言统计/框架识别
│   │   │   ├── tool_datetime.py      ← ★ 当前时间/时区/日期计算
│   │   │   ├── tool_calc.py          ← ★ 安全数学计算
│   │   │   ├── tool_task.py          ← task_status + task_list + task_log
│   │   │   ├── tool_task_manager.py  ← 任务看板：add_task / update_task
│   │   │   ├── tool_ocr.py           ← ☆ P1 OCR 文字识别（PaddleOCR）
│   │   │   └── tool_extract_archive.py ← 压缩解压 + Zip Slip 防护（§3.7.2）
│   │   ├── mcp/                  ← MCP 协议工具
│   │   │   ├── mcp_loader.py         ← MCP 加载器
│   │   │   └── tool_mcp_manager.py   ← MCP 自助安装（用 mcp-auto-install 现成方案）
│   │   └── utils.py              ← strip_ansi, _best_decode, _decode_clixml
│   │
│   ├── sandbox/                  ← Docker 沙箱
│   │   ├── config.py             ← SandboxConfig 数据类
│   │   ├── path_validator.py     ← PathValidator（路径安全验证）
│   │   ├── manager.py            ← SandboxManager（容器生命周期）
│   │   └── builder.py            ← Dockerfile 生成 + 镜像构建
│   │
│   ├── usage/
│   │   ├── sqlite_tracker.py     ← SqliteUsageTracker（IUsageTracker 的 SQLite 实现）
│   │   ├── pricing.py            ← PricingFetcher（价格获取 + 缓存）
│   │   └── hooks.py              ← UsageTrackerHook（HookService 自动记录）
│   │
│   ├── policies/                 ← Casbin 初始化配置
│   │   ├── model.conf            ← Casbin 模型
│   │   ├── policy.csv            ← Casbin 策略
│   │   └── casbin_setup.py       ← Casbin 初始化
│   │
│   ├── permission_checker.py     ← 权限检查（file/term/git/test, allow/ask/deny）
│   ├── terminal.py               ← 用户手动 PTY（精简版，无 AI 注入）
│   ├── hooks.py                  ← 事件钩子实现
│   └── background.py             ← 后台任务管理
│
├── interface/                    ← 接口层（唯一 Web 入口）
│   └── web/
│       ├── server.py             ← app 声明 + 路由注册
│       ├── routes/
│       │   ├── chat.py           ← /api/chat SSE
│       │   ├── config.py         ← /api/config/*
│       │   ├── files.py          ← /api/files, /api/file, /api/tree
│       │   ├── sessions.py       ← 历史会话
│       │   ├── health.py         ← 健康检查
│       │   ├── upload.py         ← 文件上传 + 压缩解压
│       │   ├── rollback.py       ← Git 回滚
│       │   ├── agent.py          ← /api/agent/status + /api/agent/stop
│       │   ├── history.py        ← /api/history/search
│       │   ├── usage.py          ← /api/usage/*（用量查询）
│       │   ├── tasks.py          ← /api/tasks/*（任务看板 CRUD + 搜索）
│       │   └── feedback.py       ← /api/feedback/suggestion（建议反馈）
│       ├── sse_queue.py          ← SSE 队列抽象
│       └── file_watcher.py       ← 文件变更监控
│
├── frontend/                     ← 前端源码
│   ├── static/                   ← Vite 构建产物（自动输出，server.py 读取此目录）
│   └── static_vite/              ← 前端源码
│       ├── package.json          ← 含 @ai-sdk/vue, mermaid, element-plus, echarts, sheetjs
│       ├── vite.config.js
│       ├── index.html            ← 仅 <div id="app"> 入口
│       └── src/
│           ├── main.js           ← Vue app.createApp + mount
│           ├── App.vue           ← 根组件（三栏布局 + 终端面板）
│           ├── style/
│           │   ├── variables.css
│           │   ├── terminal-themes.css
│           │   ├── theme-cyberpunk.css
│           │   ├── theme-cute.css
│           │   └── base.css
│           ├── components/
│           │   ├── layout/       ← MainLayout, ResizeHandle, StatusBar
│           │   ├── sidebar/      ← Sidebar, FileTree, FileTreeNode, Dashboard, TaskBoard
│           │   ├── editor/       ← EditorArea, EditorTabs, MonacoEditor
│           │   ├── chat/         ← ChatPanel, MessageList, InputBox, MessageItem,
│           │   │                   ChoiceCard, ChangeReviewCard, SuggestionCard,
│           │   │                   InlinePreview, LivePreview, FilePreview(多类型),
│           │   │                   DataTable, ChartView, FormGenerator, DashboardWidget,
│           │   │                   CodeExecBlock, DiffViewer, CommandCard,
│           │   │                   MemoryBubble, ThinkingIndicator, ToolCallCard,
│           │   │                   TaskListCard, ImagePreview
│           │   ├── file/         ← FilePreview 子组件（跨文件类型预览）
│           │   │   ├── ExcelViewer.vue   ← SheetJS
│           │   │   ├── PdfViewer.vue     ← PDF.js
│           │   │   ├── DocxViewer.vue    ← mammoth.js
│           │   │   └── PptxViewer.vue   ← pptxjs
│           │   ├── terminal/     ← TerminalPanel, TerminalTab, XtermViewer, OutputViewer
│           │   ├── init/         ← InitWizard, WorkspaceStep, ModelStep, ApiKeyStep
│           │   └── common/       ← MarkdownRender, CodeBlock, LoadingSpinner,
│           │                       ThemeSwitcher, CommandPalette, TaskHistoryDialog,
│           │                       RecoveryDialog ← 崩溃恢复弹窗
│           ├── composables/      ← useChat, useMessages, useTerminal, useFileTree,
│           │                       useEditor, useLayout, useMarkdownRender, useTheme,
│           │                       useCommandPalette, useTasks, useDraft, useFileDrop,
│           │                       useEventRouter, useUxEnhancements,
│           │                       useAchievements, useTimeTravel
│           └── lib/              ← xterm-setup.js, monaco-setup.js, sfc-compiler.js
│
├── scripts/                      ← 开发辅助脚本（跨平台）
│   ├── setup.py                  ← 环境初始化（检测平台 + 执行安装，核心逻辑）
│   ├── setup.bat                 ← Windows 入口：`@python scripts\setup.py`
│   ├── setup.sh                  ← Linux/Mac 入口：`python scripts/setup.py`
│   ├── seed_data.py              ← 测试数据填充
│   └── migrate_db.py             ← 数据库迁移脚本
│
├── tests/                        ← 单元测试 + 集成测试
│   ├── unit/
│   │   ├── test_router.py
│   │   ├── test_models.py
│   │   ├── test_hook_service.py
│   │   ├── test_pricing.py
│   │   └── test_permission_checker.py
│   ├── integration/
│   │   ├── test_chat_node.py
│   │   ├── test_tools.py
│   │   └── test_graph_factory.py
│   ├── fixtures/
│   ├── conftest.py
│   └── pytest.ini
├── .env.example                  ← 环境变量模板
├── Makefile                      ← 常用命令（dev/test/lint/docs/build）
├── mcp.json                      ← MCP 服务器配置（§3.7.1）
├── pyproject.toml                ← Ruff 配置 + 项目元数据（§3.8.8）
├── Dockerfile                    ← 应用容器化（§6）
├── docker-compose.yml            ← Docker Compose 编排：api + nginx（§6）
├── nginx.conf                    ← Nginx 反向代理：静态文件 + SSL 终止（§6）
└── langgraph.db                  ← SqliteSaver 持久化（自动生成）
```

---

## 与旧版树的差异对比

| 项目 | 旧树 | 新树 | 说明 |
|------|------|------|------|
| `di/` | 存在 | **已移除** | 合入 `core/container.py` |
| `core/` | 不存在 | **新增** | 应用骨架：配置加载、DI 容器、Loguru、app 工厂 |
| `domain/config/config.py` | Config 加载 + 数据类混合 | **纯数据类**（加载逻辑移入 `core/config.py`） | 分层职责清晰 |
| `domain/policies/` | 空目录（无文件） | **已移除** | Casbin 只在 `infrastructure/policies/` |
| 根级 `model.conf`, `policy.csv` | 存在（根级备份） | **已移除** | 只有 `infrastructure/policies/` 一份，避免不一致 |
| `interface/web/services/` | 子目录（2 个文件） | **已打平** | 文件直接放 `interface/web/` |
| `scripts/` | 不存在 | **新增** | 开发辅助脚本（setup/seed/migrate） |
| `.env.example` | 不存在 | **新增** | 环境变量模板 |
| `Makefile` | 不存在 | **新增** | 跨平台常用命令 |
| `domain/interfaces/` | 7 个接口 | 10 个 | 新增 iusage_tracker, ilicense_service, iupdate_service |
| `chat/` 组件 | 8 个 | **20+ 个**（分组管理） | Core 6 + Rich 3 + Preview 3 + Data 4 + Code 3 + UX 2 + Task 2 |
