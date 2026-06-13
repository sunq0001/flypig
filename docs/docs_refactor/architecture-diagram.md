# 架构图

> **来源**: `architecture-refactor.md` §2
> **关联文档**: `folder-tree.md`（文件结构）、`architecture-guide.md`（总览）、`usage-tracking.md`（用量追踪）
> 此图与主文档 §2 同步更新。

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              PRESENTATION LAYER (Web Dashboard)                                        │
│                                                                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐  首次启动/未配置时显示       │
│  │  InitWizard（初始化向导）                                                             │                              │
│  │  ├─ Step 1: WorkspaceStep  ← 选择已有工作区 or 新建                                   │                              │
│  │  ├─ Step 2: ModelStep     ← 选择模型（DeepSeek / Qwen / Claude ...）                 │                              │
│  │  └─ Step 3: ApiKeyStep    ← 录入 API Key（持久化到本地配置）                          │                              │
│  └─────────────────────────────────────────────────────────────────────────────────────┘                              │
│                                                                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                          Vue 3 + Vercel AI SDK (useChat) + Monaco Editor + xterm.js                              │   │
│  │                                                                                                                 │   │
│  │  ┌──────────────────────────┐  ┌──────────────────────────────┐  ┌──────────────────────────┐                   │   │
│  │  │   对话面板                 │  │   交互卡片区域                 │  │   终端面板                │                   │   │
│  │  │  MessageList             │  │  ChoiceCard                  │  │  XtermViewer             │                   │   │
│  │  │  MessageItem             │  │  ChangeReview                │  │  OutputViewer            │                   │   │
│  │  │  ThinkingIndicator      │  │  SuggestionCard              │  │  TerminalTab             │                   │   │
│  │  │  InputBox               │  │  ToolCallCard                │  │                          │                   │   │
│  │  │  Markdown/Mermaid       │  │  (工具调用/审批)               │  │                          │                   │   │
│  │  │  InlinePreview          │  │                              │  │                          │                   │   │
│  │  └──────────────────────────┘  └──────────────────────────────┘  └──────────────────────────┘                   │   │
│  │  ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐         │   │
│  │  │  侧边栏: 文件树(FileTree) | Dashboard | TaskBoard                                          │         │   │
│  │  └───────────────────────────────────────────────────────────────────────────────────────────────────┘         │   │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                      │ SSE (chat) + WebSocket (pty)                   │
├──────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│                                   INTERFACE LAYER (Quart — 唯一入口)                                                   │
│                                                                                                                       │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────────┐                                │
│  │  /api/chat   │ │ /api/config  │ │  /api/files   │ │  /ws/pty   │ │  /api/sessions   │                                │
│  │  (SSE流式)   │ │              │ │  + /api/tree  │ │  (手动终端) │ │  (历史会话)       │                                │
│  └──────┬──────┘ └──────────────┘ └──────────────┘ └────────────┘ └─────────────────┘                                │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────┐ ┌───────────────┐                             │
│  │ /api/roll    │ │ /api/health  │ │ /api/upload  │ │  /api/history   │ │  /api/agent    │                             │
│  │   back       │ │  (健康检查)   │ │  (文件上传)   │ │   /search      │ │  /status       │                             │
│  │  (Git回滚)   │ │              │ │  (+解压)      │ │  (历史搜索)     │ │  + /stop       │                             │
│  └─────────────┘ └──────────────┘ └──────────────┘ └────────────────┘ └───────────────┘                             │
│  ┌─────────────┐ ┌──────────────────┐                                                                                │
│  │ /api/usage   │ │ /api/feedback    │ ← 建议反馈                                                                       │
│  │  /turn       │ │  /suggestion     │                                                                                │
│  │  /session    │ │                  │                                                                                │
│  │  /range      │ │                  │                                                                                │
│  │  /cache-stats│ │                  │                                                                                │
│  └─────────────┘ └──────────────────┘                                                                                │
│       │                                                                                                               │
├───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│       ▼                                                                                                               │
│                                      APPLICATION LAYER (业务编排)                                                       │
│                                                                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  GraphFactory                                                                                                   │   │
│  │  ├─ build_graph() → 导入 domain/agent/ 下 nodes + router                                                       │   │
│  │  │  + context → 编译 StateGraph（路由注册在应用层完成）                                                          │   │
│  │  │  流程: chat → change_plan(改前预览) → exec → review → suggest                                                 │   │
│  │  └─ 工具变化时重建图（DynamicGraphFactory）                                                                      │   │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                                       │
│  ┌──────────────────────────────────────────────┐ ┌──────────────────────────────┐ ┌────────────────────────────┐    │
│  │  SuggestionEngine                            │ │  HookService                 │ │  ConfigSvc                 │    │
│  │  generate_suggestion(score) → SuggestionCard  │ │  register / emit             │ │  SessionSvc                │    │
│  │                                              │ │  (通用事件钩子)               │ │  PolicySvc                 │    │
│  └──────────────────────────────────────────────┘ └──────────────────────────────┘ └────────────────────────────┘    │
│  ┌──────────────────────────────┐ ┌──────────────────────────────┐ ┌──────────────────────────────────────┐          │
│  │  ChatService                 │ │  ContextPipeline              │ │  ConversationStore                    │          │
│  │  (中介者: graph + hook +     │ │  Truncate + Trim + Fold       │ │  IConversationStore 的 SQLite 实现      │          │
│  │   suggestion + policy 编排)  │ │  (预 LLM 上下文压缩)          │ │                                        │          │
│  │  UsageTrackerService         │ │                              │ │                                        │          │
│  │  TaskService                 │ │                              │ │                                        │          │
│  │  ☆ ExportService             │ │                              │ │                                        │          │
│  │  ☆ ModelFallbackService      │ │                              │ │                                        │          │
│  └──────────────────────────────┘ └──────────────────────────────┘ └──────────────────────────────────────┘          │
│  ┌─────────────────────────┐ ┌──────────────────────────────────┐                                                    │
│  │ GitCheckpoint Manager   │ │ SummaryGenerator                 │                                                    │
│  │ (Agent Git)             │ │ 自动生成 ≤50 字摘要              │                                                    │
│  └─────────────────────────┘ └──────────────────────────────────┘                                                    │
│                                                                                                                       │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                 DOMAIN LAYER (领域层)                                                  │
│                                                                                                                       │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  LangGraph: state.py(AgentState) + nodes.py + router.py +                                                     │   │
│  │  context.py + ToolNode + Checkpointer(SqliteSaver)                                                            │   │
│  │  AgentState: messages, turn_id, mode, persona,                                                                │   │
│  │    pending_approval, change_review, rejected_changes,                                                         │   │
│  │    change_score, adversarial_suggestion, test_results                                                         │   │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘   │
│  ┌───────────────────────┐ ┌──────────────────────────────┐ ┌──────────────────────────────┐                        │
│  │  Interfaces           │ │  Models                      │ │  PromptManager               │                        │
│  │  IModel(context驱动)   │ │  Message, ToolCall          │ │  developer(核心)             │                        │
│  │  IToolExecutor        │ │  Session, ModeConfig         │ │  reviewer(对抗)              │                        │
│  │  IConversationStore   │ │  ChoiceCard                  │ │  tester                      │                        │
│  │  IContextPipeline     │ │  ChangeScore                 │ │  architect                   │                        │
│  │  IKnowledgeStore      │ │  ExecutionMode               │ │  documenter                  │                        │
│  │  IUsageTracker        │ │  ConversationState           │ │                              │                        │
│  │  IAgent / IHook       │ │                              │ │                              │                        │
│  │  + HookContext       │ │                              │ │                              │                        │
│  └───────────────────────┘ └──────────────────────────────┘ └──────────────────────────────┘                        │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  Policies & Casbin: model.conf + policy.csv                                                                    │   │
│  │  审批分类: file(带diff) / terminal / git / test / change(审查)                                                 │   │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                                       │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                            INFRASTRUCTURE LAYER (基础设施层)                                            │
│                                                                                                                       │
│  ┌──────────────────────────┐ ┌──────────────────────────────────────────────┐ ┌────────────┐ ┌──────────────────────────┐  │
│  │ Model                    │ │  Tools（按功能分组）                           │ │ Sandbox    │ │ ConversationStore       │  │
│  │ Adapter                  │ │  edit   : 文件编辑+审查                      │ │ (Docker)   │ │ IConversationStore      │  │
│  │ openai/anthropic/local  │ │  search : 搜索+选择题                        │ │ config.py  │ │ SQLite 实现              │  │
│  │                          │ │  system : bash+任务+解压                     │ │ path_valid  │ │ 存储对话记录             │  │
│  │                          │ │  mcp    : MCP 加载器+管理                    │ │ manager    │ │                          │  │
│  │                          │ │  PermissionChecker (allow/ask/deny)         │ │ builder    │ │                          │  │
│  ├──────────────────────────┤ ├──────────────────────────────────────────────┤ ├────────────┤ ├──────────────────────────┤  │
│  │  Usage                    │ │ Terminal (PTY)                               │ │ Background │ │ Policies + Hooks         │  │
│  │  SqliteUsageTracker       │ │ 用户手动 xterm.js 终端                        │ │ 后台任务    │ │ Casbin + 事件钩子实现     │  │
│  │  ☆ LicenseService(NoOp)  │ │                                              │ │            │ │                          │  │
│  │  ☆ UpdateService(NoOp)   │ │                                              │ │            │ │                          │  │
│  │  PricingFetcher           │ │ 独立于 AI，AI 不注入命令                     │ │ 空闲自动清理│ │                          │  │
│  ├──────────────────────────┤ ├──────────────────────────────────────────────┤ ├────────────┤ ├──────────────────────────┤  │
│  │ Tasks                     │ │ Tasks Hosting                               │ │            │ │                          │  │
│  │ tool_add_task             │ │ 任务 CRUD 端点 (routes/tasks.py)              │ │            │ │                          │  │
│  │ tool_update_task          │ │ TaskListCard / TaskBoard (前端组件)           │ │            │ │                          │  │
│  └──────────────────────────┘ └──────────────────────────────────────────────┘ └────────────┘ └──────────────────────────┘  │
│                                                                                                                       │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                             DI CONTAINER (依赖注入容器)                                                │
│  Container.configure() → 装配:                                                                                      │
│    IModel / IToolExecutor / IConversationStore / IContextPipeline / IUsageTracker / PolicyService / PromptManager    │
│    IKnowledgeStore(NoOp) / GraphFactory / SuggestionEngine / HookService                                             │
│  create_agent() → 返回 IAgent (一张图统一 Graph，context 约束内 LLM 自行决定)                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Mermaid 架构图

```mermaid
flowchart TD
    subgraph PRESENTATION["🎨 表现层"]
        direction TB
        P0["InitWizard（初始化向导）<br/>WorkspaceStep / ModelStep / ApiKeyStep<br/>→ 配置存在时自动跳过"]
        P1["Vue 3 + Vercel AI SDK (useChat)<br/>+ Monaco Editor + xterm.js"]
        P2["💬 对话面板<br/>MessageList / MessageItem / ThinkingIndicator<br/>InputBox / Markdown / Mermaid / LivePreview"]
        P3["📇 对话框富组件<br/>ChoiceCard / ChangeReview / SuggestionCard<br/>InlinePreview / CodeExecBlock / DataTable<br/>DiffViewer / CommandCard / FilePreview"]
        P4["🖥️ 终端面板<br/>XtermViewer / OutputViewer / TerminalTab"]
        P5["📁 侧边栏<br/>FileTree / Dashboard / TaskBoard"]
    end
    PRESENTATION -->|"SSE<br/>+<br/>WS"| INTERFACE

    subgraph INTERFACE["🔌 接口层"]
        direction TB
        I1["/api/chat (SSE流式)<br/>/api/config · /api/files · /api/tree"]
        I2["/ws/pty (手动终端)<br/>/api/sessions · /api/rollback"]
        I3["/api/health · /api/upload<br/>/api/history/search · /api/agent<br/>/api/feedback/suggestion"]
        I4["/api/usage/*<br/>(用量查询: turn/session/range/cache-stats)"]
    end
    INTERFACE --> APPLICATION

    subgraph APPLICATION["⚙️ 应用层"]
        direction TB
        A1["GraphFactory（图构建）<br/>SuggestionEngine（对抗建议）<br/>HookService（事件钩子）"]
        A2["ConfigSvc · SessionSvc<br/>PolicySvc（Casbin）"]
        A3["ContextPipeline（预 LLM 压缩）<br/>GitCheckpointManager · SummaryGenerator"]
        A4["ChatService（中介者编排）<br/>UsageTrackerService（用量追踪）<br/>@hook 自动记录 turn/call"]
        A5["SSE 事件（18 种）:<br/>token/reasoning/choice/suggestion<br/>code_exec/inline_preview/chart<br/>data_table/command/file_preview<br/>+ response_end 含用量摘要"]
    end
    APPLICATION --> DOMAIN

    subgraph DOMAIN["📦 领域层"]
        direction TB
        D1["LangGraph 状态机<br/>state.py / nodes.py / router.py<br/>context.py / ToolNode / Checkpointer"]
        D2["AgentState<br/>messages / turn_id / mode / persona<br/>pending_approval / change_review / ..."]
        D3["Interfaces<br/>IModel / IToolExecutor<br/>IConversationStore / IContextPipeline<br/>IKnowledgeStore / IUsageTracker<br/>IAgent / IHook"]
        D4["Models<br/>Message / ToolCall / Session / ModeConfig<br/>ChoiceCard / ChangeScore / ExecutionMode<br/>ConversationState / exceptions.py"]
        D5["PromptManager<br/>developer / reviewer / tester<br/>architect / documenter"]
        D6["Casbin 权限<br/>model.conf / policy.csv<br/>allow / ask / deny"]
    end
    DOMAIN --> INFRASTRUCTURE

    subgraph INFRASTRUCTURE["🔧 基础设施层"]
        direction TB
        F1["Model Adapter<br/>openai / anthropic / local"]
        F2["Tools（4组）<br/>📝 edit/ 文件编辑+审查<br/>🔍 search/ 搜索+选择题<br/>⚡ system/ bash+任务+解压<br/>🔌 mcp/ 加载+管理"]
        F3["Sandbox（Docker）<br/>ConversationStore（SQLite）<br/>Usage（SqliteUsageT+PricingFetcher）<br/>PermissionChecker<br/>Terminal（PTY）/ Background"]
    end

    subgraph DI["💉 DI 容器"]
        direction TB
        DX1["Container.configure()"]
        DX2["装配全部依赖"]
        DX3["create_agent() → IAgent"]
    end

    DI -.->|注入应用层| APPLICATION
    DI -.->|注入领域层| DOMAIN
    DI -.->|注入基础设施| INFRASTRUCTURE

    style PRESENTATION fill:#BBDEFB,stroke:#1565C0,stroke-width:3px,fontSize:16px
    style INTERFACE fill:#FFE0B2,stroke:#E65100,stroke-width:3px,fontSize:16px
    style APPLICATION fill:#C8E6C9,stroke:#2E7D32,stroke-width:3px,fontSize:16px
    style DOMAIN fill:#E1BEE7,stroke:#6A1B9A,stroke-width:3px,fontSize:16px
    style INFRASTRUCTURE fill:#FFCDD2,stroke:#C62828,stroke-width:3px,fontSize:16px
    style DI fill:#FFF9C4,stroke:#F57F17,stroke-width:3px,fontSize:16px
```
