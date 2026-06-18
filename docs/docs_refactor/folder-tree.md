# 项目文件夹树（统一标准）

> **来源**: 全文档提取（`architecture-refactor.md` §3.1-§10）
> **关联文档**: `architecture-guide.md`（总览）、`backend-modules.md`（模块职责）、`usage-tracking.md`（usage/ 模块）
> **本树是唯一标准**，所有内联文件夹树以此为准。改结构时只需改这里，其他地方删掉冗余树。

---

## 目标文件夹树

> 图例：`←` 标准分隔符｜`★` MVP 当前实现｜`☆` P1/P2 未来预留接口

```
flypig/
│
├── __main__.py                   ← ★ 入口点（DI 初始化 + 启动）
│
├── core/                         ← ★ 应用骨架（胶水代码）
│   ├── __init__.py
│   ├── config.py                 ← ★ 配置加载（从 YAML/环境变量）
│   ├── container.py              ← ★ dependency-injector 配置
│   ├── logging.py                ← ★ Loguru 初始化
│   ├── events.py                 ← ★ 启动/关闭事件
│   └── app.py                    ← ★ Quart app 工厂
│
├── domain/                       ← ★ 领域层（接口、数据类、prompt、节点——定义 AI 是什么）
│   ├── __init__.py
│   ├── interfaces/               ← ★ 抽象接口
│   │   ├── imodel.py             ← ★ IModel（LLM 适配器：统一 stream + context 接口，DeepSeek/Claude/GPT 各有实现）
│   │   ├── itool_executor.py     ← ★ IToolExecutor（含 MCP 动态注册）
│   │   ├── iconversation_store.py  ← ★ IConversationStore（对话存储 + 检索）
│   │   ├── icontext_pipeline.py   ← ★ IContextPipeline（预 LLM 压缩）
│   │   ├── iusage_tracker.py     ← ★ IUsageTracker（用量追踪接口）
│   │   ├── ilicense_service.py   ← ☆ P2 许可激活接口（NoOp 预留）
│   │   ├── iupdate_service.py    ← ☆ P2 自动更新接口（NoOp 预留）
│   │   ├── ihook.py              ← ★ IHook（事件钩子）
│   │   ├── iagent.py             ← ★ IAgent
│   │   ├── isearch.py            ← ★ ISearch（全文/语义/代码结构搜索抽象）
│   │   ├── iknowledge_graph.py   ← ☆ IKnowledgeGraph（代码关系图，P1，长期知识）
│   │   ├── ivector_store.py      ← ☆ IVectorStore（语义向量检索，P2，长期记忆）
│   │   ├── iranker.py            ← ☆ IRanker（多源结果融合排序，P2）
│   │   ├── iast_parser.py        ← ★ IASTParser（AST 解析：symbol→行号，P0 NoOp）
│   │   └── ilsp_diagnostics.py   ← ★ ILspDiagnostics（LSP 诊断，P0 NoOp）
│   │
│   ├── agent/                    ← ★ LangGraph（领域层只定义节点和状态）
│   │   ├── state.py              ← ★ AgentState TypedDict（纯数据，零依赖）
│   │   ├── nodes.py              ← ★ 节点函数（chat/ask_choice/execute/lint/review/suggest）
│   │   ├── router.py             ← ★ 条件边路由逻辑（基于 tool_calls）
│   │   └── context.py            ← ★ Explore/Plan/Execute context 约束
│   │
│   ├── models/                   ← ★ 领域数据类（Message/Session/Task 等）
│   │   ├── message.py            ← ★ Message, ToolCall, ChoiceCard
│   │   ├── session.py            ← ★ Session
│   │   ├── mode.py               ← ★ ExecutionMode 枚举 + ModeConfig
│   │   ├── change_score.py       ← ★ ChangeScore（§3.8.9）
│   │   └── task.py               ← ★ TaskItem + user_feedback（ok/good/not_work）+ TaskStats
│   │
│   ├── prompts/                  ← ★ prompt 系统
│   │   ├── __init__.py           ← ★ 导出 MultiRoleManager
│   │   ├── multirole_manager.py  ← ★ MultiRoleManager（按角色+模型+会话维度选择 prompt）
│   │   └── roles/                ← ★ 角色 prompt 库（多 agent / 多视角通用）
│   │       ├── developer.md     ← ★ 主身份（含 user_feedback 推断指令）
│   │       ├── reviewer.md      ← ★ 审查视角：从代码质量角度挑毛病
│   │       ├── tester.md        ← ★ 测试视角：关注边界情况和脆弱性
│   │       ├── architect.md     ← ★ 架构视角：评估模块耦合和扩展性
│   │       └── documenter.md    ← ★ 文档视角：检查注释和接口可读性
│   │
│   ├── config/                   ← ★ 配置数据类（纯数据，无 IO）
│   │   ├── config.py             ← ★ Config dataclass
│   │   └── model_registry.py     ← ★ ModelRegistry dataclass
│   └── exceptions.py             ← ★ 统一异常
│
├── orchestration/                ← ★ 编排层（服务编排，非 UI 入口）
│   ├── chat_service.py           ← ★ 对话编排：调用 LangGraph → 事件分发
│   ├── config_service.py         ← ★ 配置管理
│   ├── session_service.py        ← ★ 会话状态管理
│   ├── policy_service.py         ← ★ Casbin 封装
│   ├── graph_factory.py          ← ★ 图构建：读取 graph_config.yaml → 组装 nodes + router → 编译 StateGraph
│   ├── graph_config.yaml         ← ☆ 图构建配置（P1 配置驱动化，MVP 硬编码建图）
│   ├── suggestion_engine.py      ← ★ 评分→建议映射：generate_suggestion()
│   ├── event_subscriptions.py    ← ★ 事件订阅编排：声明哪个模块订阅哪些事件
│   ├── git_checkpoint_manager.py ← ★ Agent Git checkpoint 管理
│   ├── checkpoint_store.py       ← ★ CheckpointStore：turn_id → commit_hash → summary（长期存储）
│   ├── context_pipeline.py       ← ★ 短期记忆：预 LLM 上下文压缩（Truncate+Trim+Fold，每轮从 ConversationStore 读取后压缩）
│   ├── conversation_store.py     ← ★ 长期记忆：对话/checkpoint/任务/user_feedback/用量统一 SQLite 存储（6 表）
│   ├── usage_tracker_service.py  ← ★ 用量追踪编排（IUsageTracker + PricingFetcher）
│   ├── export_service.py         ← ☆ P1 导入/导出服务（NotImplemented 预留）
│   ├── model_fallback_service.py ← ☆ P1 多模型 fallback（P0 仅记录）
│   └── summary_generator.py      ← ★ 自动生成短语摘要

│
├── infrastructure/               ← ★ 基础设施层
│   ├── llm/                      ← ★ LLM API 驱动（DeepSeek/Claude/GPT 各有实现）
│   │   ├── openai_adapter.py     ← ★ OpenAI/DeepSeek 兼容（国产主力）
│   │   ├── anthropic.py          ← ★ Claude 适配
│   │   └── local.py              ← ★ 本地模型（Ollama/vLLM, 预留）
│   │
│   ├── tools/                    ← ★ 工具执行（按功能分组）
│   │   ├── __init__.py
│   │   ├── executor.py           ← ★ ToolExecutor 主类（调度器）
│   │   ├── file/                 ← ★ 文件操作（CRUD）
│   │   │   ├── tool_read.py          ← ★ 读文件（支持 start/end 范围 / symbol 符号定位）
│   │   │   ├── tool_write.py         ← ★ 写文件（新建/全量重写）
│   │   │   ├── tool_patch_file.py    ← ★ 局部更新（按 anchor 定位修改）
│   │   │   ├── tool_delete.py        ← ★ 删除文件
│   │   │   └── tool_list_dir.py      ← ★ 列出目录内容（deep=False 看一层，deep=True 递归+语言统计）
│   │   ├── review/               ← ★ 代码审查（改完后检查质量）
│   │   │   ├── tool_change_review.py ← ★ 变更审查数据生成（§3.8.7）
│   │   │   ├── tool_lint.py          ← ★ 代码规范自动检查（Ruff, §3.8.8）
│   │   │   └── tool_change_score.py  ← ★ 变更影响评分（§3.8.9）
│   │   ├── search/               ← ★ 搜索调研（从项目/网络获取信息）
│   │   │   ├── tool_search.py        ← ★ grep + find_files
│   │   │   ├── tool_search_tools.py  ← ★ 懒加载协议：按 query 搜索工具 schema
│   │   │   ├── tool_call_direct.py   ← ★ 懒加载协议：按名直接调工具
│   │   │   └── tool_web_search.py    ← ☆ P1 内置网络搜索（DuckDuckGo）
│   │   ├── interact/             ← ★ 交互选择（出选择题让用户选）
│   │   │   └── tool_ask_choice.py    ← ★ Explore 选择题（§3.6.3）
│   │   ├── system/                 ← ★ 系统工具（bash/git/任务/解压等）
│   │   │   ├── tool_bash.py          ← ★ subprocess 命令（无 PTY）
│   │   │   ├── tool_git.py           ← ★ Git 操作代替裸 bash：status/diff/log/commit/branch
│   │   │   ├── tool_fetch_url.py     ← ★ 网页抓取（httpx，零依赖）
│   │   │   ├── tool_datetime.py      ← ★ 当前时间/时区/日期计算
│   │   │   ├── tool_calc.py          ← ★ 安全数学计算
│   │   │   ├── tool_task.py          ← ★ task_status + task_list + task_log
│   │   │   ├── tool_task_manager.py  ← ★ 任务看板：add_task / update_task / update_feedback
│   │   │   ├── tool_ocr.py           ← ☆ P1 OCR 文字识别（PaddleOCR）
│   │   │   └── tool_extract_archive.py ← ★ 压缩解压 + Zip Slip 防护（§3.7.2）
│   │   ├── mcp/                  ← ★ MCP 协议工具
│   │   │   ├── tool_mcp_loader.py    ← ★ 加载 MCP 服务器并注册到 ToolNode
│   │   │   └── tool_mcp_manager.py   ← ★ MCP 自助安装（用 mcp-auto-install 现成方案）
│   │   └── utils.py              ← ★ 工具辅助函数（ANSI 清理/编码解码）
│   │
│   ├── sandbox/                  ← ★ Docker 沙箱
│   │   ├── sandbox_config.py     ← ★ SandboxConfig 数据类
│   │   ├── path_validator.py     ← ★ PathValidator（路径安全验证）
│   │   ├── sandbox_manager.py    ← ★ SandboxManager（容器生命周期 + 状态检测，失败降级时通知前端显示沙箱/本地标识）
│   │   └── builder.py            ← ★ Dockerfile 生成 + 镜像构建
│   │
│   ├── usage/                      ← ★ 用量追踪（存入 conversation.db 的 turn_usages/call_usages 表）
│   │   ├── sqlite_tracker.py     ← ★ SqliteUsageTracker（IUsageTracker 实现，共享 conversations.db）
│   │   ├── pricing.py            ← ★ PricingFetcher（价格获取 + 缓存）
│   │   └── usage_handler.py       ← ★ 用量事件处理器（订阅 hooks，自动记录 token/cost）
│   │
│   ├── search/                    ← ★ 长期记忆：代码理解服务（被工具/节点调用，AI 不直接调）
│   │   ├── search_grep.py        ← ★ MVP: grep 全文搜索（实现 ISearch）
│   │   ├── search_ast.py         ← ☆ P1: tree-sitter AST 搜索（实现 ISearch）
│   │   ├── ast_parser.py         ← ★ P0: tree-sitter AST 解析（实现 IASTParser）
│   │   ├── lsp_diagnostics.py    ← ★ P0: pyright LSP 诊断（实现 ILspDiagnostics）
│   │   ├── search_kg.py          ← ☆ P1: 知识图谱查询（实现 IKnowledgeGraph）
│   │   ├── search_vector.py      ← ☆ P2: 向量语义检索（实现 IVectorStore）
│   │   └── search_ranker.py      ← ☆ P2: 多源排序器（实现 IRanker）
│   │
│   ├── policies/                 ← ★ 权限系统
│   │   ├── model.conf            ← ★ Casbin 模型
│   │   ├── policy.csv            ← ★ Casbin 策略
│   │   ├── casbin_setup.py       ← ★ Casbin 初始化
│   │   └── permission_checker.py ← ★ 权限检查（file/term/git/test, allow/ask/deny）
│   ├── process_manager.py        ← ★ 后台进程管理器（tool_task / /api/agent/stop 共用）
│   └── hooks.py                  ← ★ 事件钩子系统（register / emit）
│
├── backend/                      ← ★ 后端入口（HTTP 路由 + SSE + 终端，与 frontend/ 对应）
│   ├── server.py                 ← ★ app 声明 + 路由注册
│   ├── terminal.py               ← ★ 用户手动 PTY（WebSocket，无 AI 注入）
│   ├── routes/
│   │   ├── chat.py               ← ★ /api/chat SSE
│   │   ├── config.py             ← ★ /api/config/*
│   │   ├── files.py              ← ★ /api/files, /api/file, /api/tree
│   │   ├── sessions.py           ← ★ 历史会话
│   │   ├── health.py             ← ★ 健康检查
│   │   ├── upload.py             ← ★ 文件上传 + 压缩解压
│   │   ├── rollback.py           ← ★ Git 回滚
│   │   ├── agent_routes.py       ← ★ /api/agent/status + /api/agent/stop
│   │   ├── history.py            ← ★ /api/history/search
│   │   ├── usage.py              ← ★ /api/usage/*（用量查询）
│   │   ├── tasks.py              ← ★ /api/tasks/*（任务看板 CRUD + 搜索）
│   │   └── feedback.py           ← ★ /api/feedback/suggestion（建议反馈）
│   ├── sse_queue.py              ← ★ SSE 队列抽象
│   └── file_watcher.py           ← ★ 文件变更监控
│
├── frontend/                     ← ★ 前端源码
│   ├── static/                   ← ★ Vite 构建产物（自动输出，server.py 读取此目录）
│   └── static_vite/              ← ★ 前端源码
│       ├── package.json          ← ★ 含 @ai-sdk/vue, mermaid, element-plus, echarts, sheetjs
│       ├── vite.config.js
│       ├── index.html            ← ★ 仅 <div id="app"> 入口
│       └── src/
│           ├── main.js           ← ★ Vue app.createApp + mount
│           ├── App.vue           ← ★ 根组件（三栏布局 + 终端面板）
│           ├── style/
│           │   ├── variables.css
│           │   ├── terminal-themes.css
│           │   ├── theme-cyberpunk.css
│           │   ├── theme-cute.css
│           │   └── base.css
│           ├── components/
│           │   ├── layout/       ← ★ MainLayout, ResizeHandle, StatusBar（含后台进程指示器）
│           │   ├── sidebar/      ← ★ Sidebar, FileTree, FileTreeNode, Dashboard（含反馈打标）, TaskBoard
│           │   ├── editor/       ← ★ EditorArea, EditorTabs, MonacoEditor
│           │   ├── chat/         ← ★ ChatPanel, MessageList, InputBox, MessageItem,
│           │   │                   ChoiceCard, ChangeReviewCard, SuggestionCard,
│           │   │                   InlinePreview, LivePreview, FilePreview(多类型),
│           │   │                   DataTable, ChartView, FormGenerator, DashboardWidget,
│           │   │                   CodeExecBlock, DiffViewer, CommandCard,
│           │   │                   MemoryBubble(☆), ThinkingIndicator, ToolCallCard（含沙箱/本地标识）,
│           │   │                   TaskListCard, ImagePreview
│           │   ├── file/         ← ☆ FilePreview 子组件（跨文件类型预览，P1）
│           │   │   ├── ExcelViewer.vue   ← ☆ SheetJS（P1）
│           │   │   ├── PdfViewer.vue     ← ☆ PDF.js（P1）
│           │   │   ├── DocxViewer.vue    ← ☆ mammoth.js（P1）
│           │   │   └── PptxViewer.vue   ← ☆ pptxjs（P1）
│           │   ├── terminal/     ← ★ TerminalPanel, TerminalTab, XtermViewer, OutputViewer
│           │   ├── init/         ← ★ InitWizard, WorkspaceStep, ModelStep, ApiKeyStep
│           │   └── common/       ← ★ MarkdownRender, CodeBlock, LoadingSpinner,
│           │                       ThemeSwitcher, CommandPalette, TaskHistoryDialog,
│           │                       RecoveryDialog ← ★ 崩溃恢复弹窗
│           ├── composables/      ← ★ useChat, useMessages, useTerminal, useFileTree,
│           │                       useEditor, useLayout, useMarkdownRender, useTheme,
│           │                       useCommandPalette, useTasks, useDraft, useFileDrop,
│           │                       useEventRouter, useUxEnhancements,
│           │                       useAchievements(☆), useTimeTravel(☆)
│           └── lib/              ← ★ xterm-setup.js, monaco-setup.js, sfc-compiler.js
│
├── scripts/                      ← ★ 运维脚本（跨平台：setup_env.bat / .sh 双入口）
│   ├── setup_env.py              ← ★ 环境初始化（核心逻辑：检测平台 + 安装依赖 + 配置）
│   ├── setup_env.bat             ← ★ Windows 入口：`python scripts\setup_env.py`
│   ├── setup_env.sh              ← ★ Linux/Mac 入口：`python scripts/setup_env.py`
│   ├── seed_data.py              ← ★ 测试数据填充
│   └── migrate_db.py             ← ★ 数据库迁移
│
├── tests/                        ← ★ 单元测试 + 集成测试
│   ├── unit/
│   │   ├── test_router.py
│   │   ├── test_models.py
│   │   ├── test_event_subscriptions.py
│   │   ├── test_pricing.py
│   │   └── test_permission_checker.py
│   ├── integration/
│   │   ├── test_chat_node.py
│   │   ├── test_tools.py
│   │   └── test_graph_factory.py
│   ├── fixtures/
│   ├── conftest.py
│   └── pytest.ini
├── .env.example                  ← ★ 环境变量模板
├── Makefile                      ← ★ 常用命令（dev/test/lint/docs/build）
├── mcp.json                      ← ★ MCP 服务器配置（§3.7.1）
├── pyproject.toml                ← ★ Ruff 配置 + 项目元数据（§3.8.8）
├── Dockerfile                    ← ★ 应用容器化（§6）
├── docker-compose.yml            ← ★ Docker Compose 编排：api + nginx（§6）
├── nginx.conf                    ← ★ Nginx 反向代理：静态文件 + SSL 终止（§6）
├── data/
    └── conversations.db          ← ★ 统一数据库：对话/任务/checkpoint/用量 6 表（自动生成）
```

---


