## Mermaid 架构图

```mermaid
flowchart TD
    subgraph PRESENTATION["🎨 表现层 · Web Dashboard"]
        direction TB
        VUE["Vue 3 + Vercel AI SDK(useChat) + Monaco Editor + xterm.js"]
        CHAT["💬 对话面板
            MessageList · MessageItem · ThinkingIndicator
            InputBox · MarkdownRender · Mermaid · LivePreview"]
        CARDS["📇 交互卡片
            ChoiceCard · ChangeReviewCard
            SuggestionCard · ToolCallCard(审批)"]
        TERM["🖥️ 终端面板
            XtermViewer(PTY) · OutputViewer(只读) · TerminalTab"]
        SIDE["📁 侧边栏
            FileTree · FileTreeNode
            未来: Dashboard(监控/成本)"]
    end

    subgraph INTERFACE["🔌 接口层 · Quart 唯一入口"]
        direction LR
        api1["/api/chat(SSE流式)"] --- api2["/api/config"]
        api3["/api/files+/tree"] --- api4["/ws/pty(手动终端)"]
        api5["/api/sessions(会话)"] --- api6["/api/rollback(回滚)"]
        api7["/api/health(健康)"] --- api8["/api/upload(文件+解压)"]
        api9["/api/history/search"] --- api10["/api/agent/status+/stop"]
    end

    subgraph APPLICATION["⚙️ 应用层 · 业务编排"]
        direction TB
        GF["GraphFactory
            build_graph → 导入nodes+router+context
            编译 StateGraph · 工具变化重建"]
        SE["SuggestionEngine
            generate_suggestion(score)
            → SuggestionCard"]
        HS["HookService
            register(event_type, hook)
            emit(event_type, data)
            场景: pre_run·post_tool·sse_output"]
        SVC["基础服务
            ConfigSvc · SessionSvc · PolicySvc"]
        CP["回滚服务
            GitCheckpointManager(Agent Git)
            CheckpointStore(SQLite turn→hash)
            SummaryGenerator(≤50字)"]
    end

    subgraph DOMAIN["📦 领域层 · 核心逻辑"]
        direction TB
        LG["LangGraph 状态机
            state.py · nodes.py · router.py · context.py
            ToolNode · Checkpointer(SqliteSaver)
            AgentState:
              messages · turn_id · mode · persona
              pending_approval · change_review
              rejected_changes · change_score
              adversarial_suggestion · test_results"]
        IF["接口定义(7+)
            IModel · IToolExecutor · ICostTracker
            IRepository · IKnowledgeStore
            IHistoryStore · IAgent · IHook+HookContext"]
        MDL["数据模型
            Message · ToolCall · Session · ModeConfig
            ChoiceCard · ChangeScore · ExecutionMode
            ConversationState · exceptions.py"]
        PM["PromptManager
            5 角色按需懒加载
            developer(核心) · reviewer(对抗)
            tester · architect · documenter"]
        CAS["Casbin 权限
            model.conf + policy.csv
            审批分类: file(带diff) / terminal / git / test
            三档: allow(直接) / ask(弹卡) / deny(禁止)"]
    end

    subgraph INFRASTRUCTURE["🔧 基础设施层 · 具体实现"]
        direction TB
        MA["模型适配(多种)
            openai_adapter.py · anthropic.py · local.py"]
        TOOLS["工具执行(按功能分组)"]
        TE["📝 edit/ : 文件编辑+审查
            tool_file · tool_change_review
            tool_lint(Ruff) · tool_change_score"]
        TS["🔍 search/ : 搜索+选择题
            tool_search · tool_ask_choice"]
        TY["⚡ system/ : bash+任务+解压
            tool_bash · tool_task · tool_extract_archive"]
        TM["🔌 mcp/ : MCP加载+管理
            mcp_loader · tool_mcp_manager(基于mcp-auto-install)"]
        O1["Sandbox(Docker隔离) · Repository(SQLAlchemy)
            CostTracker · PermissionChecker(allow/ask/deny)
            Terminal(用户PTY) · BackgroundTasks
            HookService实现(hooks.py)"]
    end

    subgraph DI["💉 依赖注入容器"]
        direction TB
        DIT["Container.configure()"]
        DIL["装配所有依赖:"]
        DI1["IModel · IToolExecutor · ICostTracker · IRepository"]
        DI2["IHistoryStore(NoOp) · PolicyService · PromptManager"]
        DI3["IKnowledgeStore(NoOp) · GraphFactory"]
        DI4["SuggestionEngine · HookService"]
        DIO["create_agent() → 返回 IAgent"]
    end

    PRESENTATION -->|HTTP / SSE / WebSocket| INTERFACE
    INTERFACE -->|调用| APPLICATION
    APPLICATION -->|调用接口| DOMAIN
    DOMAIN -->|接口实现| INFRASTRUCTURE

    DI -->|注入 Model 适配器| INFRASTRUCTURE
    DI -->|注入 GraphFactory 等| APPLICATION
    DI -->|注入接口实现| DOMAIN

    style PRESENTATION fill:#BBDEFB,stroke:#1565C0,color:#0D47A1,stroke-width:3px
    style INTERFACE fill:#FFE0B2,stroke:#E65100,color:#BF360C,stroke-width:3px
    style APPLICATION fill:#C8E6C9,stroke:#2E7D32,color:#1B5E20,stroke-width:3px
    style DOMAIN fill:#E1BEE7,stroke:#6A1B9A,color:#4A148C,stroke-width:3px
    style INFRASTRUCTURE fill:#FFCDD2,stroke:#C62828,color:#B71C1C,stroke-width:3px
    style DI fill:#FFF9C4,stroke:#F57F17,color:#E65100,stroke-width:3px
```

> **读图方式**：5 层分层架构 + 独立 DI 容器。箭头 = 依赖方向。DI 分别注入到 Application / Domain / Infrastructure 三层。每层独立色系：蓝(前端) → 橙(接口) → 绿(应用) → 紫(领域) → 红(基础设施) → 黄(DI)。

> **来源**: `architecture-refactor.md` §2
> **关联文档**: `folder-tree.md`（文件结构）、`architecture-guide.md`（总览）
> 此图与主文档 §2 同步更新。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       PRESENTATION LAYER (Web Dashboard)                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │     Vue 3 + Vercel AI SDK (useChat) + Monaco Editor + xterm.js    │   │
│  │                                                                   │   │
│  │  ┌──────────────────────┐  ┌──────────────────┐  ┌──────────────┐ │   │
│  │  │  对话面板              │  │  交互卡片区域     │  │  终端面板     │ │   │
│  │  │  MessageList          │  │  ChoiceCard      │  │  XtermViewer  │ │   │
│  │  │  MessageItem          │  │  ChangeReview    │  │  OutputViewer │ │   │
│  │  │  ThinkingIndicator   │  │  SuggestionCard  │  │  TerminalTab  │ │   │
│  │  │  InputBox            │  │  ToolCallCard    │  │               │ │   │
│  │  │  Markdown/Mermaid    │  │  (工具调用/审批)   │  │               │ │   │
│  │  │  LivePreview         │  │                  │  │               │ │   │
│  │  └──────────────────────┘  └──────────────────┘  └──────────────┘ │   │
│  │  ┌──────────────────────────────────────────────────────────┐    │   │
│  │  │  侧边栏: 文件树(FileTree)  |  未来Dashboard(监控/成本)   │    │   │
│  │  └──────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │ SSE (chat) + WebSocket (pty)       │
├────────────────────────────────────┼─────────────────────────────────────┤
│                   INTERFACE LAYER (Quart — 唯一入口)                      │
│                                                                          │
│  ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐ ┌──────────────┐ │
│  │ /api/chat │ │/api/config│ │ /api/files │ │ /ws/pty │ │/api/sessions │ │
│  │ (SSE流式) │ │           │ │+ /api/tree │ │(手动终端)│ │(历史会话)    │ │
│  └────┬─────┘ └───────────┘ └───────────┘ └─────────┘ └──────────────┘ │
│  ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌────────────┐ ┌──────────┐  │
│  │/api/roll │ │/api/health│ │/api/upload│ │/api/history│ │/api/agent│  │
│  │  back    │ │(健康检查)  │ │(文件上传) │ │  /search   │ │ /status  │  │
│  │(Git回滚) │ │           │ │(+解压)    │ │(历史搜索)  │ │+ /stop   │  │
│  └──────────┘ └───────────┘ └───────────┘ └────────────┘ └──────────┘  │
│       │                                                                 │
├───────┼─────────────────────────────────────────────────────────────────┤
│       ▼                                                                 │
│              APPLICATION LAYER (业务编排)                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  GraphFactory                                                     │   │
│  │  ├─ build_graph() → 导入 domain/agent/ 下 nodes + router         │   │
│  │  │  + context → 编译 StateGraph（路由注册在应用层完成）            │   │
│  │  └─ 工具变化时重建图（DynamicGraphFactory）                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────┐ ┌──────────────────┐ ┌─────────────┐  │
│  │  SuggestionEngine            │ │  HookService     │ │ ConfigSvc   │  │
│  │  generate_suggestion(score)  │ │  register/emit   │ │ SessionSvc  │  │
│  │  → SuggestionCard            │ │  (通用事件钩子)   │ │ PolicySvc   │  │
│  └──────────────────────────────┘ └──────────────────┘ └─────────────┘  │
│  ┌─────────────────┐ ┌──────────────────┐ ┌─────────────────────────┐  │
│  │ GitCheckpoint   │ │ CheckpointStore  │ │ SummaryGenerator        │  │
│  │ Manager         │ │ SQLite 映射表    │ │ 自动生成 ≤50 字摘要    │  │
│  │ (Agent Git)     │ │ turn_id→hash    │ │                         │  │
│  └─────────────────┘ └──────────────────┘ └─────────────────────────┘  │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                     DOMAIN LAYER (领域层)                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LangGraph: state.py(AgentState) + nodes.py + router.py +       │   │
│  │  context.py + ToolNode + Checkpointer(SqliteSaver)              │   │
│  │  AgentState: messages, turn_id, mode, persona,                  │   │
│  │    pending_approval, change_review, rejected_changes,           │   │
│  │    change_score, adversarial_suggestion, test_results           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌───────────────────┐ ┌────────────────────┐ ┌────────────────────────┐│
│  │  Interfaces       │ │  Models            │ │  PromptManager         ││
│  │  IModel(context驱动)│ │  Message, ToolCall │ │  多角色按需懒加载      ││
│  │  IToolExecutor    │ │  Session, ModeConfig│ │  developer(核心)       ││
│  │  ICostTracker     │ │  ChoiceCard        │ │  reviewer(对抗)        ││
│  │  IRepository      │ │  ChangeScore       │ │  tester                ││
│  │  IKnowledgeStore  │ │  ExecutionMode     │ │  architect             ││
│  │  IHistoryStore    │ │  ConversationState │ │  documenter            ││
│  │  IAgent / IHook   │ │  exceptions.py     │ │                        ││
│  │  + HookContext    │ │                    │ │                        ││
│  └───────────────────┘ └────────────────────┘ └────────────────────────┘│
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Policies & Casbin: model.conf + policy.csv                      │   │
│  │  审批分类: file(带diff)/terminal/git/test/change(审查)           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                  INFRASTRUCTURE LAYER (基础设施层)                          │
│                                                                          │
│  ┌────────┐ ┌──────────────────────────┐ ┌─────────┐ ┌──────────────┐  │
│  │ Model  │ │  Tools（按功能分组）       │ │ Sandbox │ │ Repository   │  │
│  │ Adapter│ │  edit/  : 文件编辑+审查    │ │ (Docker)│ │ SQLAlchemy   │  │
│  │(多种)  │ │  search/: 搜索+选择题      │ │         │ │ + IHistory   │  │
│  │        │ │  system/: bash+任务+解压   │ │         │ │   Store(预留)│  │
│  │        │ │  mcp/   : MCP 加载器+管理  │ │         │ │              │  │
│  └────────┘ └──────────────────────────┘ └─────────┘ └──────────────┘  │
│  ┌────────┐ ┌─────────────────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Cost   │ │ PermissionChecker   │ │ Terminal │ │ Background +    │  │
│  │ Tracker│ │ file/term/git/test  │ │ (用户PTY)│ │ HookService      │  │
│  │        │ │ allow/ask/deny      │ │          │ │ 实现(hooks.py)   │  │
│  └────────┘ └─────────────────────┘ └──────────┘ └──────────────────┘  │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                     DI CONTAINER (依赖注入容器)                            │
│  Container.configure() → 装配:                                          │
│    IModel / IToolExecutor / ICostTracker / IRepository                  │
│    IHistoryStore(NoOp) / PolicyService / PromptManager                 │
│    IKnowledgeStore(NoOp) / GraphFactory / SuggestionEngine / HookService │
│  create_agent() → 返回 IAgent (一张图统一 Graph，context 约束内 LLM 决定路径)
└─────────────────────────────────────────────────────────────────────────┘
```
