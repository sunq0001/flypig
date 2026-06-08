# 架构图

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

## Mermaid 架构图

```mermaid
flowchart TD
    subgraph PRESENTATION["🎨 表现层"]
        direction TB
        P0["Vue 3 + Vercel AI SDK (useChat)<br/>+ Monaco Editor + xterm.js"]
        P1["💬 对话面板<br/>MessageList / MessageItem / ThinkingIndicator<br/>InputBox / Markdown / Mermaid / LivePreview"]
        P2["📇 卡片区域<br/>ChoiceCard / ChangeReview<br/>SuggestionCard / ToolCallCard"]
        P3["🖥️ 终端面板<br/>XtermViewer / OutputViewer / TerminalTab"]
        P4["📁 侧边栏<br/>FileTree / 未来Dashboard"]
    end
    PRESENTATION -->|"SSE<br/>+<br/>WS"| INTERFACE

    subgraph INTERFACE["🔌 接口层"]
        direction TB
        I1["/api/chat (SSE流式)<br/>/api/config · /api/files · /api/tree"]
        I2["/ws/pty (手动终端)<br/>/api/sessions · /api/rollback"]
        I3["/api/health · /api/upload<br/>/api/history/search · /api/agent"]
    end
    INTERFACE --> APPLICATION

    subgraph APPLICATION["⚙️ 应用层"]
        direction TB
        A1["GraphFactory（图构建）<br/>SuggestionEngine（对抗建议）<br/>HookService（事件钩子）"]
        A2["ConfigSvc · SessionSvc<br/>PolicySvc（Casbin）"]
        A3["GitCheckpointManager<br/>CheckpointStore · SummaryGenerator"]
    end
    APPLICATION --> DOMAIN

    subgraph DOMAIN["📦 领域层"]
        direction TB
        D1["LangGraph 状态机<br/>state.py / nodes.py / router.py<br/>context.py / ToolNode / Checkpointer"]
        D2["AgentState<br/>messages / turn_id / mode / persona<br/>pending_approval / change_review / ..."]
        D3["Interfaces<br/>IModel / IToolExecutor / ICostTracker<br/>IRepository / IKnowledgeStore<br/>IHistoryStore / IAgent / IHook"]
        D4["Models<br/>Message / ToolCall / Session<br/>ChoiceCard / ChangeScore<br/>ExecutionMode / exceptions.py"]
        D5["PromptManager<br/>developer / reviewer / tester<br/>architect / documenter"]
        D6["Casbin 权限<br/>model.conf / policy.csv<br/>allow / ask / deny"]
    end
    DOMAIN --> INFRASTRUCTURE

    subgraph INFRASTRUCTURE["🔧 基础设施层"]
        direction TB
        F1["Model Adapter<br/>openai / anthropic / local"]
        F2["Tools（4组）<br/>📝 edit/ 文件编辑+审查<br/>🔍 search/ 搜索+选择题<br/>⚡ system/ bash+任务+解压<br/>🔌 mcp/ 加载+管理"]
        F3["Sandbox（Docker）<br/>Repository（SQLAlchemy）<br/>CostTracker / PermissionChecker<br/>Terminal（PTY）/ Background"]
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
