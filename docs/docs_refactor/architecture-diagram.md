## Mermaid 架构图

```mermaid
flowchart TD
    subgraph PRESENTATION ["🎨 表现层 · Web Dashboard"]
        direction TB
        VUE["Vue 3 + Vercel AI SDK·Monaco·xterm.js"]
        CHAT["💬 对话面板<br/>MessageList·MessageItem·ThinkingIndicator<br/>InputBox·MarkdownRender·MermaidDiagram"]
        CARDS["📇 卡片区域<br/>ChoiceCard·ChangeReviewCard<br/>SuggestionCard·ToolCallCard"]
        TERM["🖥️ 终端面板<br/>XtermViewer·OutputViewer·TerminalTab"]
        SIDE["📁 侧边栏<br/>FileTree·FileTreeNode | 未来: Dashboard"]
    end

    subgraph INTERFACE ["🔌 接口层 · Quart 唯一入口"]
        direction LR
        API1["/api/chat<br/>SSE 流式"] --- API2["/api/config<br/>配置"]
        API3["/api/files<br/>+ /api/tree"] --- API4["/ws/pty<br/>手动终端"]
        API5["/api/sessions<br/>会话"] --- API6["/api/rollback<br/>Git 回滚"]
        API7["/api/health<br/>健康检查"] --- API8["/api/upload<br/>文件上传"]
        API9["/api/history/search<br/>历史搜索"] --- API10["/api/agent/status<br/>+ /api/agent/stop"]
    end

    subgraph APPLICATION ["⚙️ 应用层 · 业务编排"]
        direction TB
        GF["GraphFactory<br/>build_graph → 编译 StateGraph<br/>工具变化时重建"]
        SE["SuggestionEngine<br/>generate_suggestion(score)<br/>→ SuggestionCard"]
        HS["HookService<br/>register / emit<br/>(pre_agent_run·post_tool_call·等)"]
        SVCS["基础服务<br/>ConfigSvc·SessionSvc·PolicySvc"]
        CP["回滚服务<br/>GitCheckpointManager<br/>CheckpointStore·SummaryGenerator"]
    end

    subgraph DOMAIN ["📦 领域层 · 核心逻辑"]
        direction TB
        LG["LangGraph 状态机<br/>state.py·nodes.py·router.py<br/>context.py·Checkpointer<br/>AgentState: turn_id·mode·persona<br/>pending_approval·change_review·等"]
        IF["接口定义<br/>IModel·IToolExecutor·ICostTracker<br/>IRepository·IKnowledgeStore<br/>IHistoryStore·IAgent·IHook"]
        MDL["模型<br/>Message·ToolCall·Session<br/>ChangeScore·ExecutionMode<br/>ConversationState·ChoiceCard"]
        PM["PromptManager<br/>5 角色懒加载<br/>developer·reviewer·tester<br/>architect·documenter"]
        CAS["Casbin 权限<br/>model.conf + policy.csv<br/>审批: file/term/git/test<br/>allow / ask / deny"]
    end

    subgraph INFRASTRUCTURE ["🔧 基础设施层 · 具体实现"]
        direction TB
        MA["模型适配<br/>openai_adapter.py<br/>anthropic.py·local.py"]
        TOOLS["工具执行 (4 组)"]
        T1["edit/<br/>tool_file·tool_lint<br/>tool_change_review<br/>tool_change_score"]
        T2["search/<br/>tool_search<br/>tool_ask_choice"]
        T3["system/<br/>tool_bash·tool_task<br/>tool_extract_archive"]
        T4["mcp/<br/>mcp_loader<br/>tool_mcp_manager<br/>(mcp-auto-install)"]
        OTHER["其他基础设施<br/>Sandbox(Docker)·Repository(SQLAlchemy)<br/>CostTracker·PermissionChecker<br/>Terminal(用户PTY)·BackgroundTasks<br/>HookService 实现(hooks.py)"]
    end

    subgraph DI ["💉 依赖注入容器"]
        DI1["Container.configure()"]
        DI2["装配: IModel·IToolExecutor·ICostTracker·IRepository<br/>IHistoryStore(NoOp)·PolicyService·PromptManager<br/>IKnowledgeStore(NoOp)·GraphFactory<br/>SuggestionEngine·HookService"]
        DI3["create_agent() → IAgent"]
    end

    PRESENTATION -->|HTTP / WebSocket| INTERFACE
    INTERFACE --> APPLICATION
    APPLICATION -->|调用接口| DOMAIN
    DOMAIN -->|接口实现| INFRASTRUCTURE
    DI -.->|注入| APPLICATION
    DI -.->|注入| DOMAIN
    DI -.->|注入| INFRASTRUCTURE

    style PRESENTATION fill:#E3F2FD,stroke:#1565C0,color:#0D47A1,stroke-width:3px
    style INTERFACE fill:#FFF3E0,stroke:#E65100,color:#BF360C,stroke-width:3px
    style APPLICATION fill:#E8F5E9,stroke:#2E7D32,color:#1B5E20,stroke-width:3px
    style DOMAIN fill:#F3E5F5,stroke:#6A1B9A,color:#4A148C,stroke-width:3px
    style INFRASTRUCTURE fill:#FFEBEE,stroke:#C62828,color:#B71C1C,stroke-width:3px
    style DI fill:#FFF8E1,stroke:#F57F17,color:#E65100,stroke-width:3px
```

> **读图方式**：从上到下 5 层 + DI 容器。箭头 = 依赖方向（Interface→Application→Domain→Infrastructure）。虚线 = DI 注入。每层独立色系便于快速定位。

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
