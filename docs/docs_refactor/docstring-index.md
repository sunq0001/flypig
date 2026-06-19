# Docstring 索引 — 文档 → 文件映射

> 写 docstring 时查此表。每行给出该文件需要的**技术栈**和**引用文档**。
> 改设计时，反查此表找到需同步更新的文件。

---

## Docstring 格式模板

每个 `.py` 文件的 module-level docstring 按此格式填写。表中每一行对应此模板中的一个或几个字段：

```python
"""
[模块名]：一句话概括（对应索引中的「一句话概括」列）

为什么做：需求场景。让任何人读了一句话就能理解这个模块存在的意义。
实现方法：核心思路（1-3句）。简明说明「怎么实现的」——参考索引中的「技术栈」列。
实现效果：用户在使用过程中能感知到的变化，以及什么样的体验。
技术栈：这个模块用到的关键库/框架/技术（直接复制索引中的「技术栈」列）

层&依赖：domain / application / infrastructure / presentation 中的哪一层，能依赖谁不能依赖谁。
细节见文档：docs/docs_refactor/xxx.md → §章节 → 子标题（复制索引中的「引用文档」列）
"""
```

### 各字段对应关系

| 索引列 | docstring 中的段落 | 填写方式 |
|-------|-----------------|---------|
| 一句话概括 | 第一行 `[模块名]：` | 直接复制 |
| 技术栈 | `技术栈：` 段落 | 直接复制 |
| 引用文档 | `细节见文档：` 段落 | 直接复制，多个文档用顿号分隔 |
| — | `为什么做` | 从引用文档中提取需求背景 |
| — | `实现方法` | 从技术栈+引用文档中概括核心思路 |
| — | `实现效果` | 从引用文档中提取用户可感知的变化 |
| — | `层&依赖` | 按 architecture-guide.md §核心原则 填写 |

---

## core/

| 文件 | 一句话概括 | 技术栈 | 引用文档 |
|------|-----------|--------|---------|
| `__init__.py` | core 包声明 | — | architecture-guide.md §重构动机 |
| `config.py` | 统一配置加载 | pydantic-settings, PyYAML, python-dotenv, dataclasses | backend-modules.md §配置即代码、tech-stack.md §配置 |
| `container.py` | 单点 DI 装配 | dependency-injector, async init, test override | backend-modules.md §DI 容器、architecture-guide.md §DI 单点装配、tech-stack.md §DI 容器 |
| `logging.py` | Loguru 日志初始化 | loguru (file rotation, async write, colorized output) | tech-stack.md §日志系统、resilience.md §日志系统 |
| `events.py` | 生命周期事件 | asyncio, Signal/Event bus | resilience.md §启动恢复流程 |
| `app.py` | Quart App 工厂 | Quart, CORS, SSE, Hypercorn | backend-modules.md §Backend Layer、data-flow.md §后端数据流、tech-stack.md §Web 框架 |

---

## domain/

| 文件 | 一句话概括 | 技术栈 | 引用文档 |
|------|-----------|--------|---------|
| `__init__.py` | domain 包声明 | — | architecture-guide.md §核心原则 |
| `exceptions.py` | 统一异常体系 | BaseAppException → DomainError/InfraError/ConfigError | backend-modules.md §异常 |
| `interfaces/__init__.py` | 接口包声明 | — | — |
| `imodel.py` | LLM 模型适配接口 | IModel ABC, stream + context, DeepSeek/Claude/GPT 统一 | backend-modules.md §模型适配、langgraph-graph.md §chat 节点 |
| `itool_executor.py` | 工具执行器接口 | IToolExecutor ABC, MCP 动态注册, tool_call → 原始结果 | tools.md §核心哲学、subprocess.md §执行策略 |
| `iconversation_store.py` | 对话存储接口 | IConversationStore ABC, SQLite/S3 可替换, 7 表 CRUD | mem_convStore.md §所有表、mem_convStore_tasks.md |
| `icontext_pipeline.py` | 上下文压缩接口 | IContextPipeline ABC, budget 预算, CompositePipeline | short-term-memory.md §接口、§内置三层 |
| `iusage_tracker.py` | 用量追踪接口 | IUsageTracker ABC, turn/call 级 token/cost/cache, NoOp 可替换 | mem_convStore_usage.md §概述、tech-stack.md §IUsageTracker |
| `ilicense_service.py` | 许可激活接口 (P2 预留) | IUpdateService ABC, NoOp 默认实现 | — |
| `iupdate_service.py` | 自动更新接口 (P2 预留) | IUpdateService ABC, NoOp 默认实现 | — |
| `ihook.py` | 事件钩子接口 | IHook ABC, priority 排序, register/emit, WebHook/LogHook | resilience.md §TurnCheckpointHook |
| `iagent.py` | Agent 接口 | IAgent ABC | langgraph-graph.md §一张图 |
| `isearch.py` | 搜索抽象接口 | ISearch ABC, grep/AST/vector 多实现 | tech-stack.md §代码检索 |
| `iknowledge_graph.py` | 知识图谱接口 (P1 预留) | IKnowledgeGraph ABC | tech-stack.md §知识图谱 |
| `ivector_store.py` | 向量检索接口 (P2 预留) | IVectorStore ABC | tech-stack.md §向量检索 |
| `iranker.py` | 多源排序接口 (P2 预留) | IRanker ABC, FlashRank | tech-stack.md §多源排序 |
| `iast_parser.py` | AST 解析接口 | IASTParser ABC, tree-sitter, symbol→行号 | tech-stack.md §AST 解析 |
| `ilsp_diagnostics.py` | LSP 诊断接口 | ILspDiagnostics ABC, pyright CLI | tech-stack.md §LSP 诊断 |
| `agent/__init__.py` | agent 包声明 | — | langgraph-graph.md §节点定义 |
| `state.py` | AgentState TypedDict | typing.TypedDict, messages/turn_id/mode/context/confirmation | langgraph-graph.md §AgentState、tech-stack.md §对话状态机 |
| `nodes.py` | LangGraph 节点函数 | LangGraph nodes, chat/ask_choice/execute/lint/review/suggest | langgraph-graph.md §全路径一览 |
| `router.py` | 条件边路由逻辑 | LangGraph conditional_edges, tool_calls 判断, 4 种条件边 | langgraph-graph.md §Router |
| `context.py` | 模式 context 约束 | Explore/Plan/Execute 工具列表/温度/身份 prompt | mode-matrix.md §工具可用性明细 |
| `models/__init__.py` | models 包声明 | — | — |
| `message.py` | 消息/工具调用/选择题数据类 | @dataclass, Message/ToolCall/ChoiceCard | api-reference.md §SSE 事件格式 |
| `session.py` | 会话数据类 | @dataclass, Session, restore | backend-modules.md §SessionService |
| `mode.py` | 模式枚举 + 配置 | ExecutionMode enum, ModeConfig | mode-matrix.md §核心矩阵 |
| `change_score.py` | 变更评分 | @dataclass, ChangeScore: TRIVIAL/LOW/MEDIUM/HIGH/CRITICAL | adversarial-system.md §ChangeScore |
| `task.py` | 任务数据类 | @dataclass, TaskItem + user_feedback + TaskStats | mem_convStore_tasks.md §任务状态 |
| `prompts/__init__.py` | prompts 包声明 | — | — |
| `multirole_manager.py` | 多角色 Prompt 管理器 | MultiRoleManager, 按角色+模型+会话维度选 prompt, ~50 行自研 | tech-stack.md §MultiRoleManager |
| `roles/developer.md` | 主身份 prompt | 含 user_feedback 推断指令 | langgraph-graph.md §chat 节点 |
| `roles/reviewer.md` | 代码审查视角 | 从代码质量角度挑毛病 | adversarial-system.md §变更审查 |
| `roles/tester.md` | 测试视角 | 关注边界情况和脆弱性 | adversarial-system.md §对抗体系 |
| `roles/architect.md` | 架构视角 | 评估模块耦合和扩展性 | adversarial-system.md §对抗体系 |
| `roles/documenter.md` | 文档视角 | 检查注释和接口可读性 | adversarial-system.md §对抗体系 |
| `config/__init__.py` | config 包声明 | — | — |
| `config.py` | Config dataclass | @dataclass, 项目/模型/模式/API Key 配置 | backend-modules.md §配置即代码 |
| `model_registry.py` | ModelRegistry dataclass | @dataclass, 模型清单 + provider/temperature | backend-modules.md §配置即代码 |

---

## orchestration/

| 文件 | 一句话概括 | 技术栈 | 引用文档 |
|------|-----------|--------|---------|
| `__init__.py` | orchestration 包声明 | — | — |
| `chat_service.py` | 对话编排主服务 | LangGraph, SSE 事件分发, receive → invoke → dispatch, ~60 行 | data-flow.md §后端数据流、backend-modules.md §ChatService |
| `config_service.py` | 配置管理服务 | Config 初始化/模型切换/API Key 管理, ~80 行 | backend-modules.md §ConfigService |
| `session_service.py` | 会话状态管理 | 多会话 CRUD + restore() 断点恢复, ~100 行 | backend-modules.md §SessionService、resilience.md §崩溃恢复 |
| `policy_service.py` | Casbin 权限封装 | pycasbin, allow/ask/deny, ~80 行 | backend-modules.md §PolicyService、mode-matrix.md §权限矩阵 |
| `graph_factory.py` | StateGraph 编译工厂 | LangGraph StateGraph, 导入 nodes+router → 编译, ~80 行 | backend-modules.md §GraphFactory、langgraph-graph.md §一张图 |
| `graph_config.yaml` | 图构建配置 (P1) | YAML, 节点/边/工具列表配置 | backend-modules.md §GraphFactory |
| `suggestion_engine.py` | 评分→建议映射 | generate_suggestion(), ~40 行自研 | adversarial-system.md §对抗建议、backend-modules.md §SuggestionEngine |
| `event_subscriptions.py` | 事件订阅编排 | hook register/emit, 声明谁订阅哪些事件, ~60 行 | backend-modules.md §EventSubscriptions |
| `git_checkpoint_manager.py` | Git Checkpoint 管理 | git init/commit/restore, mapping→conversation_store 的 turn_id→commit_hash, ~80 行 | mem_convStore_checkpoints.md §Git Checkpoint、backend-modules.md §GitCheckpointManager |
| `context_pipeline.py` | 上下文压缩管线 | CompositePipeline, Truncate+Fold+Trim 三层, SQLAlchemy 读取 | short-term-memory.md §职责、§内置三层 |
| `conversation_store.py` | 统一 SQLite 存储 | SQLAlchemy ORM, conversations.db 7 表, WAL 模式 | mem_convStore.md §所有表、mem_convStore_tasks.md§任务状态 |
| `usage_tracker_service.py` | 用量追踪编排 | IUsageTracker + PricingFetcher, EventSubscriptions 自动记录, ~60 行 | mem_convStore_usage.md §数据模型、backend-modules.md §UsageTrackerService |
| `export_service.py` | 导入/导出服务 (P1) | NotImplemented 预留 | — |
| `model_fallback_service.py` | 多模型 Fallback (P1) | P0 仅记录错误 | — |
| `summary_generator.py` | 短语摘要生成 | 根据本轮交互生成 ≤50 字摘要, ~40 行 | backend-modules.md §SummaryGenerator |

---

## infrastructure/

| 文件 | 一句话概括 | 技术栈 | 引用文档 |
|------|-----------|--------|---------|
| `__init__.py` | infrastructure 包声明 | — | — |
| `llm/__init__.py` | LLM 适配包声明 | — | — |
| `openai_adapter.py` | OpenAI/DeepSeek 兼容适配 | OpenAI SDK, stream=True, context 管理 | backend-modules.md §模型适配、tech-stack.md §AI 模型 SDK |
| `anthropic.py` | Claude 适配 | Anthropic SDK, 消息格式转换 | backend-modules.md §模型适配 |
| `local.py` | 本地模型适配 (预留) | Ollama/vLLM 兼容接口 | backend-modules.md §模型适配 |
| `tools/__init__.py` | 工具包声明 | — | — |
| `tools/executor.py` | ToolExecutor 调度器 | LangGraph ToolNode, tool_call → 执行 → 原始结果 | tools.md §核心哲学、subprocess.md §执行策略 |
| `tools/utils.py` | 工具辅助函数 | ANSI 清理/编码解码/通用格式 | tools.md §附录 |
| `tools/file/__init__.py` | 文件工具子包 | — | — |
| `tool_read.py` | 安全文件读取 | aiofiles, start/end 范围, symbol 符号定位, magic bytes 检测 | tools.md §文件编辑方案 |
| `tool_write.py` | 新建/全量重写 | aiofiles, 写入前审批检查 | tools.md §文件编辑方案 |
| `tool_patch_file.py` | 局部锚点更新 | Aider 编辑引擎 / git apply, anchor 定位, 回退策略 | tools.md §文件编辑方案 |
| `tool_delete.py` | 删除文件 | os.remove, 安全确认 | tools.md §文件编辑方案 |
| `tool_list_dir.py` | 列出目录结构 | Path.rglob, collections.Counter, deep/浅层 | tools.md §文件编辑方案、tech-stack.md §项目扫描 |
| `tools/review/__init__.py` | 审查工具子包 | — | — |
| `tool_change_review.py` | 变更审查数据生成 | diff_excerpt, risk 自评, 结构化成 plan | adversarial-system.md §ChangePlan |
| `tool_lint.py` | 代码规范检查 | subprocess ruff --fix, 自动修复 | tech-stack.md §代码规范检查 |
| `tool_change_score.py` | 变更影响评分 | ChangeScore: TRIVIAL→CRITICAL 5 级, 自动/通知/阻塞审批 | adversarial-system.md §ChangeScore |
| `tools/search/__init__.py` | 搜索工具子包 | — | — |
| `tool_search.py` | grep + find_files | subprocess grep, Path.rglob, 文件内容/结构搜索 | tech-stack.md §代码检索 |
| `tool_search_tools.py` | 懒加载工具搜索 | 按 query 搜索工具 schema | tools.md §工具注册 |
| `tool_call_direct.py` | 懒加载工具直接调用 | 按名直接调工具 | tools.md §工具注册 |
| `tool_web_search.py` | 网络搜索 (P1) | duckduckgo-search, httpx | tech-stack.md §内置搜索 |
| `tools/interact/__init__.py` | 交互工具子包 | — | — |
| `tool_ask_choice.py` | 选择题卡片 | 结构化 return {choices}, ~20 行 | langgraph-graph.md §Explore 模式、mode-matrix.md §工具可用性 |
| `tools/system/__init__.py` | 系统工具子包 | — | — |
| `tool_bash.py` | subprocess 命令执行 | subprocess.run, 超时控制, 无 PTY | subprocess.md §执行策略 |
| `tool_git.py` | Git 操作封装 | GitPython, status/diff/log/commit/branch 结构化返回 | tech-stack.md §Git 操作、tools.md §回滚 |
| `tool_fetch_url.py` | 网页抓取 | httpx + trafilatura, HTML→纯文本去噪 | tech-stack.md §网页抓取 |
| `tool_datetime.py` | 当前时间/时区/日期计算 | datetime + pytz, ~5 行 | tech-stack.md §日期时间 |
| `tool_calc.py` | 安全数学计算 | ast.literal_eval + Decimal, ~15 行 | tech-stack.md §安全计算 |
| `tool_task.py` | 后台任务管理 | subprocess.Popen, 环形缓冲区, task_status/task_list/task_log | tech-stack.md §后台任务 |
| `tool_task_manager.py` | 任务看板 CRUD | add_task/update_task/update_feedback, 写入 conversations.db | mem_convStore_tasks.md §CRUD |
| `tool_ocr.py` | OCR 文字识别 (P1) | PaddleOCR | tech-stack.md §OCR |
| `tool_extract_archive.py` | 压缩解压 + Zip Slip 防护 | zipfile/tarfile/py7zr, 路径穿越检测 | tech-stack.md §压缩解压、tools.md §安全 |
| `tools/mcp/__init__.py` | MCP 工具子包 | — | — |
| `tool_mcp_loader.py` | MCP 服务器加载注册 | mcp-auto-install, 启动时加载 mcp.json → ToolNode | mcp.md §三层策略 |
| `tool_mcp_manager.py` | MCP 自助安装 | 调 mcp-auto-install 的 install_mcp_server 工具 | mcp.md §第二层+第三层 |
| `sandbox/__init__.py` | 沙箱子包 | — | — |
| `sandbox_config.py` | 沙箱配置数据类 | @dataclass, Docker 配置 + 资源限制 | subprocess.md §沙箱策略 |
| `path_validator.py` | 路径安全验证 | 白名单/黑名单/cwd 限制, 越权弹 SuggestionCard | subprocess.md §沙箱路径验证 |
| `sandbox_manager.py` | Docker 容器生命周期 | Docker SDK, check/down 降级通知 | subprocess.md §执行策略 |
| `builder.py` | Dockerfile 生成 + 镜像构建 | Docker SDK build | subprocess.md §沙箱配置 |
| `usage/__init__.py` | 用量追踪子包 | — | — |
| `sqlite_tracker.py` | SQLite 用量追踪 | SQLAlchemy, turn_usage/call_usage 表, ~80 行 | mem_convStore_usage.md §数据模型 |
| `pricing.py` | 价格获取 + 缓存 | PricingFetcher, 模型价格快照→model_pricing 表 | mem_convStore_usage.md §模型定价 |
| `usage_handler.py` | 用量事件处理器 | 订阅 hooks, 自动记录 token/cost, 不自动处理 | mem_convStore_usage.md §核心哲学 |
| `search/__init__.py` | 代码理解子包 | — | — |
| `search_grep.py` | grep 全文搜索 (MVP) | subprocess grep, Path.rglob, 实现 ISearch | tech-stack.md §代码检索 |
| `search_ast.py` | AST 搜索 (P1) | tree-sitter / ast-grep, 结构匹配 | tech-stack.md §结构化代码搜索 |
| `ast_parser.py` | AST 符号→行号解析 | tree-sitter, 实现 IASTParser | tech-stack.md §AST 解析 |
| `lsp_diagnostics.py` | LSP 诊断 | pyright CLI, 实现 ILspDiagnostics | tech-stack.md §LSP 诊断 |
| `search_kg.py` | 知识图谱查询 (P1) | 自研 ~300 行 AST 关系抽取, 实现 IKnowledgeGraph | tech-stack.md §知识图谱 |
| `search_vector.py` | 向量语义检索 (P2) | sentence-transformers + SQLite, 实现 IVectorStore | tech-stack.md §向量检索 |
| `search_ranker.py` | 多源排序器 (P2) | 自研 ~50 行 + FlashRank, 实现 IRanker | tech-stack.md §多源排序 |
| `policies/__init__.py` | 权限子系统包 | — | — |
| `model.conf` | Casbin 模型文件 | pycasbin, ACL/RBAC/ABAC 模型定义 | backend-modules.md §PolicyService、tech-stack.md §权限策略 |
| `policy.csv` | Casbin 策略文件 | CSV, sub/obj/act, allow/ask/deny | backend-modules.md §PolicyService |
| `casbin_setup.py` | Casbin 初始化 | pycasbin Enforcer, model.conf + policy.csv 加载 | backend-modules.md §PolicyService |
| `permission_checker.py` | 权限检查执行 | file/term/git/test, check_permission(), allow/ask/deny | backend-modules.md §PermissionChecker |
| `hooks.py` | 事件钩子系统 | register/emit, priority 排序, TurnCheckpointHook 默认启用 | resilience.md §TurnCheckpointHook |
| `process_manager.py` | 后台进程管理 | subprocess.Popen, 生命周期/清理/状态查询 | tech-stack.md §后台任务 |

---

## backend/

| 文件 | 一句话概括 | 技术栈 | 引用文档 |
|------|-----------|--------|---------|
| `__init__.py` | backend 包声明 | — | — |
| `server.py` | Quart 应用 + 路由注册 | Quart, blueprint, SSE, CORS, Hypercorn | backend-modules.md §Web 层、api-reference.md §REST 端点 |
| `terminal.py` | 用户手动终端 WebSocket | Quart WebSocket, xterm.js, 无 AI 注入 | subprocess.md §用户 PTY、data-flow.md §终端数据流 |
| `routes/__init__.py` | 路由子包 | — | — |
| `chat.py` | SSE 聊天路由 | Quart SSE, ChatService → LangGraph, ≤120 行 | api-reference.md §SSE 事件格式、data-flow.md §后端数据流 |
| `config.py` | 配置查询/修改 | Quart, ConfigService, GET/PUT, ≤80 行 | api-reference.md §REST 端点 |
| `files.py` | 文件操作路由 | Quart, read/write/tree, ≤80 行 | api-reference.md §REST 端点 |
| `sessions.py` | 历史会话路由 | Quart, SessionService, CRUD + restore | api-reference.md §REST 端点 |
| `health.py` | 健康检查 | Quart, GET, 容器/DB/模型状态 | api-reference.md §REST 端点 |
| `upload.py` | 文件上传 + 解压 | Element Plus Upload + 后端 zipfile, 拖拽 | api-reference.md §REST 端点 |
| `rollback.py` | Git 回滚 | GitPython, turn_id → commit_hash, POST | api-reference.md §REST 端点 |
| `agent_routes.py` | Agent 状态/停止 | Quart, /api/agent/status + /api/agent/stop | api-reference.md §REST 端点 |
| `history.py` | 历史搜索 | Quart, FTS5/search, GET | api-reference.md §REST 端点 |
| `usage.py` | 用量查询 | Quart, turn/session/range/cache-stats | api-reference.md §REST 端点、mem_convStore_usage.md §查询 |
| `tasks.py` | 任务 CRUD + 搜索 | Quart, CRUD + search + stats + history/snapshot | api-reference.md §REST 端点、mem_convStore_tasks.md §CRUD |
| `feedback.py` | 建议反馈记录 | Quart, POST, suggestion_id + adopted | api-reference.md §REST 端点 |
| `sse_queue.py` | SSE 队列抽象 | asyncio.Queue, event 类型分发 | data-flow.md §SSE 事件流 |
| `file_watcher.py` | 文件变更监控 | watchdog, 文件修改→通知前端 | data-flow.md §文件变更流 |

---

## frontend/static_vite/

| 文件 | 一句话概括 | 技术栈 | 引用文档 |
|------|-----------|--------|---------|
| `package.json` | 前端依赖声明 | @ai-sdk/vue, element-plus, mermaid, echarts, monaco-editor, xterm, lucide | frontend-arch.md §技术栈、tech-stack.md §前端 |
| `vite.config.js` | Vite 构建配置 | Vite, Vue SFC, proxy API | frontend-arch.md §技术栈 |
| `index.html` | SPA 入口 | div#app 入口, 不包含任何 UI | frontend-arch.md §目标目录结构 |
| `src/main.js` | Vue app 挂载点 | Vue 3 createApp + mount, Element Plus 注册 | frontend-arch.md §目标目录结构 |
| `src/App.vue` | 根组件三栏布局 | Vue 3 SFC, MainLayout + 路由 | frontend-arch.md §目标目录结构 |
| `src/style/variables.css` | CSS 变量 | 颜色/间距/字体/断点 | frontend-arch.md §技术栈 |
| `src/style/terminal-themes.css` | 终端主题 | xterm.js 主题配色 | chat-ux.md §StatusBar |
| `src/style/theme-cyberpunk.css` | 赛博朋克主题 | CSS 变量覆盖 | chat-ux.md §主题切换 |
| `src/style/theme-cute.css` | 可爱主题 | CSS 变量覆盖 | chat-ux.md §主题切换 |
| `src/style/base.css` | 全局样式重置 | CSS reset, 布局基础 | chat-ux.md §情感设计 |
| `src/components/layout/MainLayout.vue` | 三栏主布局 | Vue, ResizeHandle, 可拖拽分栏 | chat-ux.md §布局 |
| `src/components/layout/ResizeHandle.vue` | 分栏拖拽手柄 | vue-draggable-next | chat-ux.md §布局 |
| `src/components/layout/StatusBar.vue` | 状态栏 | 模式/模型/用量/主题 | chat-ux.md §StatusBar 增强 |
| `src/components/sidebar/Sidebar.vue` | 侧边栏容器 | Vue, 文件树/任务看板切换 | frontend-arch.md §目标目录结构 |
| `src/components/sidebar/FileTree.vue` | 文件树 | Vue, 递归组件 | frontend-arch.md §目标目录结构 |
| `src/components/sidebar/FileTreeNode.vue` | 树节点 | Vue, 展开/折叠/图标 | frontend-arch.md §目标目录结构 |
| `src/components/sidebar/Dashboard.vue` | 工作区首页 | Vue, 最近工作区/快速开始/用量概览 | chat-ux.md §Welcome/Dashboard |
| `src/components/sidebar/TaskBoard.vue` | 任务看板面板 | Vue, 任务列表/状态/搜索 | mem_convStore_tasks.md §任务状态 |
| `src/components/editor/EditorArea.vue` | 编辑器区域容器 | Vue, EditorTabs + MonacoEditor | frontend-arch.md §目标目录结构 |
| `src/components/editor/EditorTabs.vue` | 文件标签栏 | Vue, 多文件切换/关闭 | frontend-arch.md §目标目录结构 |
| `src/components/editor/MonacoEditor.vue` | 代码编辑器 | Monaco Editor, Vue wrapper, diff/readonly | frontend-arch.md §技术栈 |
| `src/components/chat/ChatPanel.vue` | 对话框面板 | Vue, MessageList + InputBox, 渐进揭露 | chat-ux.md §产品哲学 |
| `src/components/chat/MessageList.vue` | 消息列表 | Vue, 虚拟滚动/自动滚动 | chat-ux.md §渐进揭露 |
| `src/components/chat/InputBox.vue` | 输入框 | Element Plus input, 拖拽文件缩略图, uuid | chat-ux.md §输入框 |
| `src/components/chat/MessageItem.vue` | 单条消息渲染 | Vue, 角色/时间/内容 | chat-ux.md §消息样式 |
| `src/components/chat/ChoiceCard.vue` | 选择题卡片 | Element Plus card, 多选/单选 | api-reference.md §choice 事件 |
| `src/components/chat/ChangeReviewCard.vue` | 变更审查卡片 | Vue, diff_excerpt, 文件列表/风险等级 | adversarial-system.md §ChangePlan |
| `src/components/chat/SuggestionCard.vue` | 对抗建议卡片 | Vue, 评分/建议/采纳/拒绝 | adversarial-system.md §对抗建议 |
| `src/components/chat/InlinePreview.vue` | 行内预览 | Vue, 代码/图片/表格 inline | chat-ux.md §反馈即预览 |
| `src/components/chat/LivePreview.vue` | 实时预览 | Vue, iframe/组件实时渲染 | chat-ux.md §反馈即预览 |
| `src/components/chat/FilePreview.vue` | 文件多类型预览 | Vue, 代码/图片/表格 多类型判断 | chat-ux.md §反馈即预览 |
| `src/components/chat/DataTable.vue` | 数据表格 | Element Plus table/echarts | chat-ux.md §渐进揭露 |
| `src/components/chat/ChartView.vue` | ECharts 图表 | echarts, 柱状图/折线图/饼图 | tech-stack.md §图表渲染 |
| `src/components/chat/FormGenerator.vue` | AI 生成表单 | Vue, AI 描述生成表单卡片 | chat-ux.md §焦点+预期 |
| `src/components/chat/DashboardWidget.vue` | 仪表盘小部件 | Vue, 用量/任务/回顾 | chat-ux.md §Dashboard |
| `src/components/chat/CodeExecBlock.vue` | 代码执行块 | Vue, 终端输出/错误/重试 | chat-ux.md §代码执行 |
| `src/components/chat/DiffViewer.vue` | Diff 对比 | Vue, 行级 diff 高亮 | chat-ux.md §变更审查 |
| `src/components/chat/CommandCard.vue` | 命令卡片 | Vue, 命令/输出/状态 | chat-ux.md §渐进揭露 |
| `src/components/chat/MemoryBubble.vue` | 记忆气泡 (P1) | Vue, 知识点提示 | chat-ux.md §记忆气泡 |
| `src/components/chat/ThinkingIndicator.vue` | 思考过程指示器 | Vue, LLM 推理进度 | api-reference.md §reasoning 事件 |
| `src/components/chat/ToolCallCard.vue` | 工具调用卡片 | Vue, 沙箱/本地标识 | chat-ux.md §工具调用 |
| `src/components/chat/TaskListCard.vue` | 任务列表卡片 | Vue, 当前轮次任务 | mem_convStore_tasks.md §任务状态 |
| `src/components/chat/ImagePreview.vue` | 图片预览 | medium-zoom, 缩略图→大图 | tech-stack.md §图片预览 |
| `src/components/file/ExcelViewer.vue` | Excel 预览 (P1) | SheetJS (xlsx), 浏览器内 workbook | tech-stack.md §Excel 预览 |
| `src/components/file/PdfViewer.vue` | PDF 预览 (P1) | PDF.js, 指定页码渲染 | tech-stack.md §PDF 预览 |
| `src/components/file/DocxViewer.vue` | Word 预览 (P1) | mammoth.js, HTML 渲染 | tech-stack.md §Word 预览 |
| `src/components/file/PptxViewer.vue` | PPT 预览 (P1) | pptxjs, 缩略图轮播 | tech-stack.md §PPT 预览 |
| `src/components/terminal/TerminalPanel.vue` | 终端面板容器 | Vue, xterm.js + 多个终端 tab | frontend-arch.md §目标目录结构 |
| `src/components/terminal/TerminalTab.vue` | 终端标签页 | Vue, tab 切换 | frontend-arch.md §目标目录结构 |
| `src/components/terminal/XtermViewer.vue` | xterm 终端 | xterm.js, Vue wrapper, WebSocket | frontend-arch.md §技术栈 |
| `src/components/terminal/OutputViewer.vue` | 只读输出查看器 | Vue, AI 命令输出展示 | frontend-arch.md §终端面板 |
| `src/components/init/InitWizard.vue` | 初始化向导 | Vue Step wizard, WorkspaceStep→ModelStep→ApiKeyStep | chat-ux.md §InitWizard |
| `src/components/init/WorkspaceStep.vue` | 工作区选择步骤 | Vue, 选择/拖入工作区 | chat-ux.md §InitWizard |
| `src/components/init/ModelStep.vue` | 模型选择步骤 | Vue, 模型列表/温度配置 | chat-ux.md §InitWizard |
| `src/components/init/ApiKeyStep.vue` | API Key 配置步骤 | Vue, Key 输入/验证 | chat-ux.md §InitWizard |
| `src/components/common/MarkdownRender.vue` | Markdown 渲染 | marked + highlight.js, 扩展 code block | frontend-arch.md §技术栈 |
| `src/components/common/CodeBlock.vue` | 代码块 | highlight.js, 复制/语言标 | frontend-arch.md §技术栈 |
| `src/components/common/LoadingSpinner.vue` | 加载动画 | Element Plus loading | chat-ux.md §情感设计 |
| `src/components/common/ThemeSwitcher.vue` | 主题切换 | Vue, 全局 CSS 变量切换 | chat-ux.md §主题切换 |
| `src/components/common/CommandPalette.vue` | 命令面板 | Vue, Ctrl+K/Cmd+K 唤出 | chat-ux.md §Command Palette |
| `src/components/common/TaskHistoryDialog.vue` | 任务历史弹窗 | Element Plus dialog, 状态变更日志 | mem_convStore_tasks.md §任务状态 |
| `src/components/common/RecoveryDialog.vue` | 崩溃恢复弹窗 | Element Plus dialog, 继续/放弃 | resilience.md §崩溃恢复 |
| `src/composables/useChat.js` | SSE 对话 + tool_call | @ai-sdk/vue useChat, onToolCall/onResponse/onError | frontend-arch.md §Vercel AI SDK |
| `src/composables/useMessages.js` | 消息状态管理 | Vue reactive, messages/loading/streaming | frontend-arch.md §数据流 |
| `src/composables/useTerminal.js` | 终端 WebSocket | WebSocket, xterm.js 集成 | frontend-arch.md §终端面板 |
| `src/composables/useFileTree.js` | 文件树状态 | fetch /api/tree, 展开/选中 | frontend-arch.md §侧边栏 |
| `src/composables/useEditor.js` | 编辑器状态 | Monaco Editor, 文件打开/编辑 | frontend-arch.md §编辑器 |
| `src/composables/useLayout.js` | 布局状态 | Vue reactive, 分栏宽度/侧边栏开关 | frontend-arch.md §布局 |
| `src/composables/useMarkdownRender.js` | Markdown 渲染扩展 | marked extension, 自定义渲染 | frontend-arch.md §Markdown |
| `src/composables/useTheme.js` | 主题切换状态 | CSS 变量, localStorage 持久化 | chat-ux.md §主题切换 |
| `src/composables/useCommandPalette.js` | 命令面板状态 | Ctrl+K, 命令搜索/执行 | chat-ux.md §Command Palette |
| `src/composables/useTasks.js` | 任务看板状态 | fetch /api/tasks, 状态过滤/排序 | mem_convStore_tasks.md §CRUD |
| `src/composables/useDraft.js` | 草稿管理 | localStorage, 输入框草稿恢复 | chat-ux.md §输入框 |
| `src/composables/useFileDrop.js` | 文件拖拽 | 拖入输入框, 缩略图预览/上传 | chat-ux.md §输入框 |
| `src/composables/useEventRouter.js` | 事件路由分发 | SSE 事件→组件分发 | api-reference.md §SSE 事件格式 |
| `src/composables/useUxEnhancements.js` | UX 增强 | 打字机/焦点/情绪价值 | chat-ux.md §情感设计 |
| `src/composables/useAchievements.js` | 成就系统 (P1) | Vue, 勋章/成就弹窗 | chat-ux.md §情感设计 |
| `src/composables/useTimeTravel.js` | 时间旅行 (P1) | Vue, 回溯历史状态 | chat-ux.md §时间旅行 |
| `src/lib/xterm-setup.js` | xterm.js 初始化 | xterm.js, addon-fit/addon-web-links, 主题加载 | frontend-arch.md §技术栈 |
| `src/lib/monaco-setup.js` | Monaco Editor 初始化 | monaco-editor, 语言/主题/快捷键 | frontend-arch.md §技术栈 |
| `src/lib/sfc-compiler.js` | Vue SFC 编译器 | @vue/compiler-sfc, 实时编译渲染 | frontend-arch.md §LivePreview |

---

## scripts/

| 文件 | 一句话概括 | 技术栈 | 引用文档 |
|------|-----------|--------|---------|
| `setup_env.py` | 跨平台环境初始化 | Python, 检测平台 + pip install + 配置文件 | operations.md §阶段式演进 |
| `setup_env.bat` | Windows 入口 | batch, `python scripts\setup_env.py` | operations.md §环境初始化 |
| `setup_env.sh` | Linux/Mac 入口 | shell, `python scripts/setup_env.py` | operations.md §环境初始化 |
| `seed_data.py` | 测试数据填充 | SQLAlchemy, 模拟对话/任务/用量 | operations.md §测试数据 |
| `migrate_db.py` | 数据库 Schema 迁移 | SQLAlchemy Alembic / 原生 SQL | resilience.md §Schema 迁移 |

---

## tests/

| 文件 | 一句话概括 | 技术栈 | 引用文档 |
|------|-----------|--------|---------|
| `conftest.py` | pytest 共享配置 | pytest fixture, DI override, test SQLite | architecture-guide.md §测试策略 |
| `pytest.ini` | pytest 配置 | asyncio, 测试标记, 覆盖率 | architecture-guide.md §测试策略 |
| `unit/test_router.py` | 路由逻辑单元测试 | pytest, mock AgentState | langgraph-graph.md §Router |
| `unit/test_models.py` | 数据类单元测试 | pytest, dataclass 构造/验证 | backend-modules.md §数据类型规范 |
| `unit/test_event_subscriptions.py` | 事件订阅测试 | pytest, mock hook | backend-modules.md §EventSubscriptions |
| `unit/test_pricing.py` | 价格计算测试 | pytest, mock API | mem_convStore_usage.md §模型定价 |
| `unit/test_permission_checker.py` | 权限检查测试 | pytest, Casbin mock | mode-matrix.md §工具可用性 |
| `integration/test_chat_node.py` | 聊天节点集成测试 | pytest-asyncio, LangGraph 编译 | langgraph-graph.md §chat 节点 |
| `integration/test_tools.py` | 工具执行集成测试 | pytest, ToolExecutor, subprocess mock | tools.md §工具执行 |
| `integration/test_graph_factory.py` | 图构建集成测试 | pytest, StateGraph verify | langgraph-graph.md §一张图 |

---

## 根级配置

| 文件 | 一句话概括 | 引用文档 |
|------|-----------|---------|
| `.env.example` | 环境变量模板 | operations.md §环境变量 |
| `pyproject.toml` | 项目元数据 + Ruff 配置 | tech-stack.md §代码规范检查 |
| `Dockerfile` | 应用容器镜像 | operations.md §Docker 镜像 |
| `docker-compose.yml` | 多服务编排 | operations.md §Docker Compose |
| `nginx.conf` | 反向代理 + 静态文件 + SSL | operations.md §Nginx |
| `mcp.json` | MCP 服务器预配清单 | mcp.md §第一层基础配置 |
| `Makefile` | 常用命令聚合 | operations.md §开发工作流 |
