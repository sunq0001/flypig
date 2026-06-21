# 技术栈

> **历史来源**: `architecture_refactor_old.md` §3.12
> **关联文档**: `architecture-guide.md`（总览）、`folder-tree.md`（文件结构）、`mem_convStore_usage.md`（成本追踪取代方案）、`resilience.md`（loguru 日志系统）
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
| | UI 组件库 | **Element Plus** | 市面方案 | 含 Tree 树形控件，直接用于文件树 |
| | 图表渲染 | **Mermaid.js** + **ECharts** | 市面方案 | Mermaid 用于流程图/时序图（文本即图表），ECharts 用于数据可视化柱状图/折线图/饼图 |
| | Markdown 扩展 | **marked + highlight.js** | 市面方案 | 扩展 code block 渲染器 |
| **后端** | Web 框架 | **Quart** | 市面方案 | ASGI，原生 WebSocket/SSE |
| | ASGI 服务器 | **Hypercorn** | 市面方案 | 生产级 |
| | AI 模型 SDK | **OpenAI SDK** | 市面方案 | 官方 SDK，stream=True；国产模型均兼容 OpenAI 格式 |
| | DI 容器 | **`dependency-injector`** | 市面方案 | 支持 async init、测试 override |
| | 数据库 ORM | **SQLAlchemy** | 市面方案 | 事实标准，SQLite→PostgreSQL 无缝切换 |
| | 权限策略 | **Casbin (pycasbin)** | 市面方案 | ACL/RBAC/ABAC 全支持 |
| | 对话状态机 | **LangGraph** | 市面方案 | 原生 state machine、Checkpointer、human-in-the-loop、ToolNode |
| | 长期记忆（P2 可选） | **LangMem** | 市面方案 | AI 主动 search/manage memory 工具；后台自动提取知识点；备选：可替换为自研 pgvector |
| | 沙箱 | **Docker SDK** | 市面方案 | Docker 容器隔离 |
| | 配置 | **PyYAML** | 市面方案 | yaml 解析 |
| | 代码规范检查 | **Ruff**（含 D 规则） | 市面方案 | Rust 编写，比 flake8 快 100 倍，支持 --fix 自动修复。`select = ["D"]` + `convention = "google"` 强制 Google 风格 docstring |
| | 日志系统 | **loguru** | 市面方案 | 1 行初始化自带文件轮转/压缩/异步写入/彩色输出，替代 stdlib logging |
| | 会话持久化 | **SQLAlchemy** | 市面方案 | 存储层用开源 ORM |
| | 历史搜索预留 | **SQLite FTS5 → pgvector → LangMem** | 混合方案 | P0: SQLite + tag 索引；P1: LangMem 语义检索（可替换为自研 pgvector） |
| | IUsageTracker | **薄包装（~80 行 SQLite CRUD）** | 薄包装 | turn/call 级 token/cost/缓存；LangFuse/Helicone 等现成方案都要独立服务部署，单用户场景太重 |
| | MultiRoleManager | **自研（~50 行）** | 业务定制 | 多角色对抗切换，无现成方案 |
| | OrchestrationService（已拆分为三） | | | 原三职合一服务拆为 GraphFactory+SuggestionEngine+EventSubscriptions |
| **工具** | Git 操作 | **GitPython** 薄封装 | 市面方案 | 裸 bash git 不可控，tool_git 结构化返回 status/diff/log/commit |
| | 网页抓取 | **httpx + trafilatura** | 市面方案 | httpx 发请求，trafilatura HTML→纯文本（去噪比 BeautifulSoup 好），不靠 MCP fetch |
| | 项目扫描 | **Path.rglob + collections.Counter** | **自写 ~20 行** | 标准库统计语言分布、文件类型、框架识别 |
| | 安全计算 | **ast.literal_eval + Decimal**（或 numexpr） | **自写 ~15 行** | 避免 AI 用 bash eval 做数学运算 |
| | 日期时间 | **datetime + pytz** | **自写 ~5 行** | 标准库，AI 需要知道当前时间/时区 |
| | bash 执行 | **subprocess（标准库）** | 市面方案 | Python 内置，无 PTY |
| | 文件操作 | **Aider 编辑引擎 或 git apply** | 市面方案 | 开源方案（Aider 或标准 git apply + unified diff） |
| | 后台任务 | **subprocess.Popen + 自研 buffer** | 混合 | 标准库执行 + 自研环形缓冲区 |
| | 代码规范检查 | **Ruff CLI** | 市面方案 | subprocess 调用 ruff --fix，自动修复 |
| | 文件上传 | **Element Plus Upload** | 市面方案 | 前端拖拽，后端接收解压 |
| | 文件树 | **@he-tree/vue3** | 市面方案 | 支持懒加载、虚拟滚动（大目录不卡）、拖拽排序、自定义图标插槽。替代自研递归组件 |
| | 代码检索（MVP） | **grep + Path.rglob** | 标准库 | Python 内置，零依赖 |
| | 结构化代码搜索 | **ast-grep** | 市面方案 | AST 级别搜索，支持跨文件模式匹配，替代 bare grep |
| | AST 解析（符号定位） | **tree-sitter** | 市面方案 | 即时解析→symbol 转行号，read_file/patch_file 内部使用 |
| | LSP 诊断（改后检查） | **pyright **(Python) **/ typescript-language-server (TS)** | 市面方案 | CLI 模式，改完代码后调一次诊断错误 |
| | 知识图谱（P1） | **自研 ~300 行**（基于 AST 关系抽取） | 业务定制 | 无现成代码知识图谱开源方案，需自研函数/类/模块关系图 |
| | 向量检索（P2） | **sentence-transformers + SQLite** | 市面方案 | 轻量嵌入，无需单独部署向量服务。备选：ChromaDB |
| | 多源排序（P2） | **自研 ~50 行 + FlashRank** | 混合 | 知识图谱/向量/grep 结果融合排序；FlashRank 作为可选的 LLM-free reranker |
| | 图片预览 | **medium-zoom** | 市面方案 | 点击对话中缩略图弹出大图查看 |
| | Excel 预览 | **SheetJS (xlsx)** | 市面方案 | 浏览器内读取 workbook，按 AI 标注行列渲染 |
| | PDF 预览 | **PDF.js** | 市面方案 | Mozilla 出品，渲染指定页码为 canvas |
| | Word 预览 | **mammoth.js** | 市面方案 | 转 HTML 渲染，AI 定位到结论段落 |
| | PPT 预览 | **pptxjs** | 市面方案 | 每页缩略图轮播，AI 标注页码自动切换 |
| | 压缩解压 | **zipfile/tarfile/py7zr** | 市面方案 | 标准库 + py7zr，含 Zip Slip 防护 |
| | OCR（P1） | **PaddleOCR** | 市面方案 | 国产中英文 OCR，比 Tesseract 效果好 |
| | 内置搜索（P1） | **duckduckgo-search** | 市面方案 | 零配置网络搜索，无需 API Key |
| | **断路器** | **自研 @circuit_breaker** | 业务定制 | 调用连续失败 5 次自动熔断 60s |
| | **重试机制** | **自研 async retry** | 业务定制 | 网络抖动自动重试，指数退避 |
| | **监控** | **prometheus_client** | 市面方案 | Counter/Histogram/Gauge，暴露 /metrics |
| | 选择题卡片 | **自研 tool_ask_choice** | 业务定制 | 核心 UX 模式，~20 行返回值 |
| | MCP 协议 | **mcp-auto-install（社区方案）** | 市面方案 | 不自研；基于官方 MCP Registry 自动搜索、安装、配置 |
| | 工具路由 | **LangGraph ToolNode** | 市面方案 | 标准 LangGraph tool node |
| **文档** | 文档站框架 | **MkDocs + mkdocstrings** | 市面方案 | 从 Python docstring 自动生成 API 文档，与现有 Markdown 文档站一体化 |
| | docstring 覆盖率 | **interrogate** | 市面方案 | `fail-under = 80`，保证 docstring 覆盖率 ≥ 80% |
| | Git 钩子 | **pre-commit** | 市面方案 | ruff D + interrogate 自动校验，不达标无法 commit |
| **DevOps** | 容器编排 | **Docker Compose** | 市面方案 | 单机足够 |

## 总结

- **开源方案 ~95%** — LangGraph + LangMem + Casbin + dependency-injector + Element Plus + Mermaid.js + Vercel AI SDK + Ruff + Quart + SQLAlchemy + marked + highlight.js + Docker + mcp-auto-install...
- **真正自研 ~3%** — MultiRoleManager(~50行)、GraphFactory(~80行)+SuggestionEngine(~40行)+EventSubscriptions(~40行)、ChangeScore(~40行)、ChangeReview(~60行)
- **薄包装不计入** — IUsageTracker(~80行 SQLite CRUD，替换 LangFuse/Helicone 等重型方案)、tool_ask_choice(~20行)、tool_lint(~20行调Ruff)、IHistoryStore(接口定义)、tool_mcp_manager(调mcp-auto-install)
