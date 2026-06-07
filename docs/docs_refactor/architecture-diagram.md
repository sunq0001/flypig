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
│  ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌────────────┐               │
│  │/api/roll │ │/api/health│ │/api/upload│ │/api/history│               │
│  │  back    │ │(健康检查)  │ │(文件上传) │ │  /search   │               │
│  │(Git回滚) │ │           │ │(+解压)    │ │(历史搜索)  │               │
│  └──────────┘ └───────────┘ └───────────┘ └────────────┘               │
│       │                                                                 │
├───────┼─────────────────────────────────────────────────────────────────┤
│       ▼                                                                 │
│              APPLICATION LAYER (业务编排)                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  OrchestrationService                                            │   │
│  │  ├─ build_graph() → 统一 LangGraph（条件路由非固定流水线）         │   │
│  │  ├─ generate_suggestion() → 根据 ChangeScore 生成对抗建议卡      │   │
│  │  └─ handle_adversarial_decision() → 用户选择后执行优化            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌────────────────────────────────┐ ┌────────────┐ ┌──────────┐        │
│  │  LangGraph (统一 Graph)         │ │ConfigSvc   │ │SessionSvc│        │
│  │  chat → router(条件边) →       │ │(配置管理)  │ │(会话持久) │        │
│  │    ask_choice / execute /      │ ├────────────┤ ├──────────┤        │
│  │    lint / change_review /      │ │PolicySvc   │ │          │        │
│  │    suggestion / approval       │ │(权限规则)  │ │          │        │
│  │  LLM 在 context 约束内自由跳转   │ └────────────┘ └──────────┘        │
│  └────────────────────────────────┘                                    │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                     DOMAIN LAYER (领域层)                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LangGraph: StateSchema + ToolNode + conditional_edges           │   │
│  │  + Checkpointer(SqliteSaver) + Human-in-the-loop + Streaming    │   │
│  │  AgentState: messages, mode, persona, phase,                     │   │
│  │    pending_approval, change_review, rejected_changes,            │   │
│  │    change_score, adversarial_suggestion, test_results            │   │
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
│  │ Model  │ │  Tools(全部工具)          │ │ Sandbox │ │ Repository   │  │
│  │ Adapter│ │  bash/file/search/task   │ │ (Docker)│ │ SQLAlchemy   │  │
│  │(多种)  │ │  ask_choice/change_review│ │         │ │ + IHistory   │  │
│  │        │ │  lint/change_score       │ │         │ │   Store(预留)│  │
│  │        │ │  extract_archive/mcp    │ │         │ │              │  │
│  │        │ │  _loader/tool_mcp_mgr   │ │         │ │              │  │
│  └────────┘ └──────────────────────────┘ └─────────┘ └──────────────┘  │
│  ┌────────┐ ┌─────────────────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Cost   │ │ PermissionChecker   │ │ Terminal │ │ Background +    │  │
│  │ Tracker│ │ file/term/git/test  │ │ (用户PTY)│ │ Casbin Setup    │  │
│  │        │ │ allow/ask/deny      │ │          │ │                 │  │
│  └────────┘ └─────────────────────┘ └──────────┘ └──────────────────┘  │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                     DI CONTAINER (依赖注入容器)                            │
│  Container.configure() → 装配:                                          │
│    IModel / IToolExecutor / ICostTracker / IRepository                  │
│    IHistoryStore(NoOp) / PolicyService / PromptManager                 │
│    IKnowledgeStore(NoOp) / OrchestrationService                        │
│  create_agent() → 返回 IAgent (一张图统一 Graph，context 约束内 LLM 决定路径)
└─────────────────────────────────────────────────────────────────────────┘
```
