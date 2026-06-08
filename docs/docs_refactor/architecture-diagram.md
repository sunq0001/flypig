## Mermaid 架构图（内容与原图一致，仅优化布局和颜色）

```mermaid
flowchart TD
    subgraph PRES["🎨 表现层 - Web Dashboard"]
        VUE["Vue 3 + Vercel AI SDK (useChat) + Monaco Editor + xterm.js"]
        P1["对话面板 MessageList · MessageItem · ThinkingIndicator · InputBox · Markdown/Mermaid · LivePreview"]
        P2["交互卡片区域 ChoiceCard · ChangeReview · SuggestionCard · ToolCallCard(工具调用/审批)"]
        P3["终端面板 XtermViewer · OutputViewer · TerminalTab"]
        P4["侧边栏: 文件树(FileTree) | 未来Dashboard(监控/成本)"]
    end

    subgraph INTF["🔌 接口层 - Quart 唯一入口"]
        direction LR
        I1["/api/chat (SSE流式)"] --- I2["/api/config"]
        I3["/api/files + /api/tree"] --- I4["/ws/pty (手动终端)"]
        I5["/api/sessions (历史会话)"] --- I6["/api/rollback (Git回滚)"]
        I7["/api/health (健康检查)"] --- I8["/api/upload (文件上传 + 解压)"]
        I9["/api/history/search (历史搜索)"] --- I10["/api/agent/status + /api/agent/stop"]
    end

    subgraph APP["⚙️ 应用层 - 业务编排"]
        GF["GraphFactory build_graph → 导入domain/agent/ nodes+router+context → 编译StateGraph (路由注册在应用层完成) 工具变化时重建图(DynamicGraphFactory)"]
        SE["SuggestionEngine generate_suggestion(score) → SuggestionCard"]
        HS["HookService register/emit (通用事件钩子)"]
        SV["ConfigSvc · SessionSvc · PolicySvc"]
        CP["GitCheckpointManager(Agent Git) · CheckpointStore(SQLite映射 turn_id→hash) · SummaryGenerator(自动生成≤50字摘要)"]
    end

    subgraph DOM["📦 领域层 - 核心逻辑"]
        LG["LangGraph: state.py(AgentState) + nodes.py + router.py + context.py + ToolNode + Checkpointer(SqliteSaver) AgentState: messages · turn_id · mode · persona · pending_approval · change_review · rejected_changes · change_score · adversarial_suggestion · test_results"]
        IFC["Interfaces: IModel(context驱动) · IToolExecutor · ICostTracker · IRepository · IKnowledgeStore · IHistoryStore · IAgent / IHook + HookContext"]
        MDL["Models: Message · ToolCall · Session · ModeConfig · ChoiceCard · ChangeScore · ExecutionMode · ConversationState · exceptions.py"]
        PM["PromptManager: 多角色按需懒加载 developer(核心) · reviewer(对抗) · tester · architect · documenter"]
        CAS["Policies & Casbin: model.conf + policy.csv 审批分类: file(带diff)/terminal/git/test/change(审查)"]
    end

    subgraph INFRA["🔧 基础设施层 - 具体实现"]
        MA["Model Adapter(多种) openai_adapter.py · anthropic.py · local.py"]
        TOLS["Tools(按功能分组)"]
        TE["edit/: 文件编辑+审查 tool_file · tool_change_review · tool_lint · tool_change_score"]
        TS["search/: 搜索+选择题 tool_search · tool_ask_choice"]
        TY["system/: bash+任务+解压 tool_bash · tool_task · tool_extract_archive"]
        TM["mcp/: MCP加载器+管理 mcp_loader · tool_mcp_manager(mcp-auto-install)"]
        OTH["CostTracker · PermissionChecker(file/term/git/test allow/ask/deny) · Terminal(用户PTY) · Background + HookService实现(hooks.py) · Sandbox(Docker) · Repository(SQLAlchemy + IHistoryStore预留)"]
    end

    subgraph DI["💉 依赖注入容器"]
        DII["Container.configure() → 装配: IModel / IToolExecutor / ICostTracker / IRepository IHistoryStore(NoOp) / PolicyService / PromptManager IKnowledgeStore(NoOp) / GraphFactory / SuggestionEngine / HookService create_agent() → 返回 IAgent (一张图统一 Graph，context约束内 LLM 决定路径)"]
    end

    PRES -->|SSE + WebSocket| INTF
    INTF --> APP
    APP -->|调用接口| DOM
    DOM -->|接口实现| INFRA
    DI -.->|注入| APP
    DI -.->|注入| DOM
    DI -.->|注入| INFRA

    style PRES fill:#BBDEFB,stroke:#1565C0,color:#0D47A1,stroke-width:3px
    style INTF fill:#FFE0B2,stroke:#E65100,color:#BF360C,stroke-width:3px
    style APP fill:#C8E6C9,stroke:#2E7D32,color:#1B5E20,stroke-width:3px
    style DOM fill:#E1BEE7,stroke:#6A1B9A,color:#4A148C,stroke-width:3px
    style INFRA fill:#FFCDD2,stroke:#C62828,color:#B71C1C,stroke-width:3px
    style DI fill:#FFF9C4,stroke:#F57F17,color:#E65100,stroke-width:3px
```

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
