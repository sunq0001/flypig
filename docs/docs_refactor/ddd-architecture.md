# DDD 架构设计

> **历史来源**: `architecture_refactor_old.md` §3.1-§10 + 多轮架构讨论决策
> **关联文档**: `folder-tree.md`（本树为核心标准）、`architecture-guide.md`（总览）、`backend-modules.md`（模块职责）、`migration-roadmap.md`（迁移步骤）、`data-flow.md`（数据流）、`langgraph-graph.md`（Agent 状态节点）
> **核心原则**: "AI suggests, user decides" — 所有路由/决策由 LLM 自然判断，不依赖关键词匹配或硬编码流水线

---

## 1. 为什么要 DDD

### 问题背景

FlyPig 是一个 AI Agent 项目，代码结构必须同时满足两个角色的需求：

| 角色 | 需求 | 痛点 |
|------|------|------|
| **AI（CodeBuddy）写代码** | 可见可推导的结构、统一的依赖方向、可预测的文件位置 | 层次混乱时 AI 不知道 import 放哪，容易引入循环依赖 |
| **人类开发者（未来 SaaS 团队）** | 明确的模块边界、可独立部署的上下文、可扩展的商业化能力 | 没有边界时多人协作互相踩脚，微服务拆分无从下手 |

### DDD 对两者的价值

| DDD 特性 | 对 AI 的价值 | 对 SaaS 的价值 |
|----------|------------|---------------|
| **Bounded Context** | 减少上下文窗口大小，AI 只需加载局部 | 微服务拆分依据 |
| **值对象 & 实体** | AI 改代码时能区分"换数据"还是"换ID" | 数据一致性保障 |
| **聚合根** | AI 不会误改跨实体一致性规则 | 事务边界明确 |
| **仓储接口** | AI 面向接口编程，不依赖具体实现 | 可切换存储后端 |
| **防腐层（ACL）** | AI 改 LLM 接入不影响核心逻辑 | 多供应商兼容 |
| **统一的依赖方向** | AI 按方向推导 import 路径，无循环依赖 | 分层清晰，维护成本低 |

---

## 2. Building Blocks 取舍策略

### Phase 1（必须从开头做）

这些 Building Blocks 在第一天就存在，因为它们是"**AI 改代码时最容犯错的地方**"，不加会引入技术债务。

| Building Block | 代码位置 | 用途 |
|---------------|----------|------|
| **值对象** | `domain/models/` 内所有 `dataclass(frozen=True)` | SessionId, MessageId, Mode, ToolCall, ChangeScore 等不变数据 |
| **实体** | `domain/models/session.py` | Session —— 有 ID + 状态机的可变对象 |
| **聚合根** | `domain/models/session.py` | Session 是核心聚合根，下属 Conversation/Task 通过它访问 |
| **工厂** | `infrastructure/tools/` 各 tool 类 | ToolFactory 模式，按需构建 tool 实例 |
| **仓储接口** | `domain/interfaces/*.py` | IConversationStore, ISearch 等 —— 面向接口不面向实现 |
| **领域服务** | `orchestration/` 层 | chat_service, config_service 等 —— 编排多个聚合/仓储完成用例 |
| **领域异常** | `domain/exceptions.py` | 统一异常层次，区分"参数错"、"不存在"、"非法状态" |
| **防腐层（ACL）** | `infrastructure/llm/`, `infrastructure/tools/` | LLM/工具/文件系统适配器，隔离第三方变化 |

### Phase 2（后续迭代自然加入）

这些在 MVP 阶段不需要特意引入，等出现实际需求再添加：

| Building Block | 触发条件 |
|---------------|----------|
| **领域事件** | 当有两个以上模块需要响应同一个状态变更时（如 Session 创建后需要通知用量模块 + 通知前端） |
| **聚合不变条件** | 当 Session 状态机出现非法跃迁时（如从 idle 直接跳到 editing 而不是 executing） |
| **规约** | 当搜索/过滤条件变得复杂（如"过去 7 天的错误会话 + 使用 DeepSeek 模型"） |
| **上下文地图** | 当团队规模 > 3 人或出现两个以上 Bounded Context |

### Phase 3（不引入）

| Building Block | 不引入理由 |
|---------------|-----------|
| **CQRS** | 读写分离太超前，当前数据量（SQLite 几 MB）用不上 |
| **Event Sourcing** | Agent 交互不是金融交易，重建状态无意义 |
| **Saga** | 分布式事务未出现，目前单体架构不需要 |

---

## 3. 完整文件夹树（DDD 标准版）

> 图例：`★` Phase 1（迁移即做）｜`☆` Phase 2（后续迭代加）｜`←` 来自 folder-tree.md 的功能补齐

```
flypig/
│
├── shared/                          ★ 共享内核（基类 + 通用模式）
│   ├── entity.py                    Entity 基类（identity + version + __eq__）
│   ├── aggregate_root.py            AggregateRoot 基类（domain_events 集合）
│   ├── value_object.py              ValueObject 基类（不可变 + 结构相等）
│   ├── factory.py                   Factory 基类（复杂对象装配）
│   ├── repository.py                Repository[T] 泛型接口
│   ├── specification.py             Specification 模式基类
│   ├── domain_event.py              DomainEvent 基类
│   └── event_bus.py                 EventBus（publish / subscribe / clear）
│
├── domain/                          ★ 领域层（拍平，最多 1 层子目录）
│   ├── __init__.py                  ★ 导出所有值对象、实体、异常
│   ├── session.py                   ★ Session 聚合根（Aggregate Root）
│   ├── session_id.py                SessionId 值对象
│   ├── session_status.py            SessionStatus 枚举值对象
│   ├── message.py                   Message 实体（Entity）
│   ├── message_id.py                MessageId 值对象
│   ├── turn.py                      Turn 值对象
│   ├── mode.py                      Mode 值对象（explore/plan/execute）
│   ├── persona.py                   Persona 值对象
│   ├── mode_matrix.py               ModeMatrix 值对象（权限矩阵）
│   ├── agent_state.py               AgentState 值对象
│   ├── graph_spec.py                GraphSpec 值对象
│   ├── chat_context.py              ChatContext 值对象
│   ├── tool_call.py                 ToolCall 值对象
│   ├── tool_result.py               ToolResult 值对象
│   ├── tool_def.py                  ToolDefinition 值对象
│   ├── change_score.py              ChangeScore 值对象
│   ├── change_review.py             ChangeReview 值对象
│   ├── suggestion_card.py           SuggestionCard 值对象
│   ├── task_item.py                 TaskItem 实体（Entity, 有 id + 状态机）
│   ├── model_ref.py                 ModelRef 值对象
│   ├── api_key.py                   ApiKey 值对象（脱敏）
│   ├── workspace.py                 Workspace 值对象
│   ├── pricing_entry.py             PricingEntry 值对象
│   ├── mcp_server.py                MCP 服务器配置值对象（name, command, args, env, status）
│   │
│   ├── prompts/                     ← ★ prompt 系统
│   │   ├── __init__.py              导出 MultiRoleManager
│   │   ├── multirole_manager.py     按角色+模型+会话选择 prompt
│   │   └── roles/                   多视角 prompt 库
│   │       ├── developer.md         ★ 主身份
│   │       ├── reviewer.md          ★ 审查视角
│   │       ├── tester.md            ★ 测试视角
│   │       ├── architect.md         ★ 架构视角
│   │       └── documenter.md        ★ 文档视角
│   │
│   ├── event/                       ☆ 领域事件（Domain Event）
│   │   ├── session_created.py
│   │   ├── session_closed.py
│   │   ├── message_sent.py
│   │   ├── message_received.py
│   │   ├── tool_called.py
│   │   └── tool_completed.py
│   │
│   ├── specification/               ☆ 规约（Specification）
│   │   ├── session_by_status.py
│   │   ├── session_by_time.py
│   │   └── session_by_user.py
│   │
│   └── exceptions.py                ★ 领域异常体系
│         FlyPigException
│         ├── DomainError
│         │   ├── SessionClosedError
│         │   ├── InvalidTurnError
│         │   └── MessageValidationError
│         ├── ConfigurationError
│         ├── ModelAPIError
│         ├── ToolExecutionError
│         └── SandboxError
│
├── orchestration/                   ★ 应用服务 + LangGraph 编排
│   ├── graph.py                     LangGraph 图定义
│   ├── state.py                     AgentState Pydantic 模型
│   ├── context.py                   上下文组装
│   ├── chat.py                      聊天应用服务（SendMessageUsecase）
│   ├── config.py                    配置应用服务
│   ├── session.py                   会话应用服务
│   ├── tool.py                      工具应用服务
│   ├── review.py                    审查应用服务
│   ├── pricing.py                   价格应用服务
│   ├── usage.py                     用量追踪应用服务
│   ├── export.py                    导出应用服务
│   ├── summary.py                   摘要生成应用服务
│   ├── git_checkpoint.py            Git 检查点服务
│   ├── event_subscriptions.py       事件订阅管理器
│   ├── policy_service.py            ← Casbin 封装（from folder-tree）
│   ├── graph_factory.py             ← 图构建：读取 graph_config.yaml → 组装 StateGraph
│   ├── graph_config.yaml            ← 图构建配置
│   ├── suggestion_engine.py         ← 评分→建议映射
│   ├── context_pipeline.py          ← 短期记忆：预 LLM 上下文压缩
│   ├── conversation_store.py        ← 长期记忆：对话/checkpoint/任务/用量 统一 SQLite 存储
│   ├── model_fallback_service.py    ← ☆ P1 多模型 fallback
│   ├── mcp.py                       ← MCP 应用服务（安装/卸载/启停/搜索 / 协调 infra 各 tool）
│   └── nodes/                       LangGraph 节点（薄层调用）
│       ├── chat_node.py
│       ├── tool_node.py
│       ├── review_node.py
│       ├── suggest_node.py
│       └── route_node.py
│
├── acl/                              ★ 防腐层（拍平，不嵌套）
│   ├── ollama.py                    Ollama /api/tags 防腐
│   ├── subprocess.py                subprocess 输出切割 + 错误翻译
│   ├── llm_api.py                   LLM API 429/401/502 统一翻译
│   ├── docker.py                    Docker SDK 异常翻译
│   ├── git.py                       Git 命令输出解析
│   ├── chat_server.py               Node chat-server 协议防腐
│   ├── license.py                   许可证校验防腐
│   └── pricing.py                   定价页 HTML 解析统一化
│   └── mcp.py                       MCP JSON-RPC 子进程输出解析 + 协议错误翻译
│
├── infrastructure/                   ★ 基础设施层
│   ├── llm/                         LLM 适配器
│   │   ├── openai_adapter.py        ★ OpenAI/DeepSeek 兼容
│   │   ├── anthropic_adapter.py     ★ Claude 适配
│   │   └── local_adapter.py         ★ 本地模型（预留）
│   │
│   ├── persistence/                 持久化实现
│   │   ├── sqlite_session_repo.py
│   │   ├── sqlite_conversation_repo.py
│   │   ├── yaml_config_repo.py
│   │   └── sqlite_pricing_repo.py
│   │
│   ├── tools/                       工具实现
│   │   ├── executor.py              ToolExecutor 调度器
│   │   ├── file/                    ← 文件 CRUD
│   │   │   ├── tool_read.py
│   │   │   ├── tool_write.py
│   │   │   ├── tool_patch_file.py
│   │   │   ├── tool_delete.py
│   │   │   └── tool_list_dir.py
│   │   ├── review/                  ← 代码审查
│   │   │   ├── tool_change_review.py
│   │   │   ├── tool_lint.py
│   │   │   └── tool_change_score.py
│   │   ├── search/                  ← 搜索调研工具
│   │   │   ├── tool_search.py
│   │   │   ├── tool_search_tools.py
│   │   │   ├── tool_call_direct.py
│   │   │   └── tool_web_search.py
│   │   ├── interact/                ← 交互选择
│   │   │   └── tool_ask_choice.py
│   │   ├── system/                  ← 系统工具
│   │   │   ├── tool_bash.py
│   │   │   ├── tool_git.py
│   │   │   ├── tool_fetch_url.py
│   │   │   ├── tool_datetime.py
│   │   │   ├── tool_calc.py
│   │   │   ├── tool_task.py
│   │   │   ├── tool_task_manager.py
│   │   │   ├── tool_ocr.py          ☆ P1
│   │   │   └── tool_extract_archive.py
│   │   ├── mcp/                     MCP 桥接
│   │   │   ├── tool_mcp_loader.py
│   │   │   ├── tool_mcp_manager.py
│   │   │   ├── tool_mcp_controller.py
│   │   │   ├── tool_mcp_discovery.py
│   │   │   └── tool_mcp_lifecycle.py
│   │   └── utils.py                 ← 辅助函数
│   │
│   ├── usage/                       ← 用量追踪
│   │   ├── sqlite_tracker.py        SqliteUsageTracker（IUsageTracker 实现）
│   │   ├── pricing.py               PricingFetcher（价格获取 + 缓存）
│   │   └── usage_handler.py         用量事件处理器
│   │
│   ├── search/                      代码理解服务
│   │   ├── ast_parser.py            ★ AST 解析（IASTParser 实现）
│   │   ├── search_grep.py           ★ MVP: grep 全文搜索
│   │   ├── search_ast.py            ☆ P1: tree-sitter AST 搜索
│   │   ├── search_kg.py             ☆ P1: 知识图谱查询
│   │   ├── search_vector.py         ☆ P2: 向量语义检索
│   │   ├── search_ranker.py         ☆ P2: 多源排序器
│   │   └── lsp_diagnostics.py       ★ LSP 诊断（ILspDiagnostics 实现）
│   │
│   ├── sandbox/                     Docker 沙箱
│   │   ├── sandbox_config.py
│   │   ├── path_validator.py
│   │   ├── sandbox_manager.py
│   │   └── builder.py
│   │
│   ├── policies/                    权限策略（Casbin）
│   │   ├── model.conf
│   │   ├── policy.csv
│   │   ├── casbin_setup.py
│   │   └── permission_checker.py
│   │
│   ├── pricing/                     价格爬虫
│   │   └── vendors/
│   ├── ollama_discovery.py          Ollama 模型发现
│   ├── process_manager.py           进程管理
│   └── hooks.py                     钩子
│
├── interface/                        ★ 接口适配层
│   ├── rest/                        REST API（Quart）
│   │   ├── middleware/
│   │   └── routes/                  （薄，只做协议转换）
│   │       ├── chat_routes.py       → 调 orchestration/chat.py
│   │       ├── config_routes.py     → 调 orchestration/config.py
│   │       ├── session_routes.py
│   │       ├── agent_routes.py
│   │       ├── files_routes.py
│   │       ├── pricing_routes.py
│   │       ├── health_routes.py
│   │       ├── feedback_routes.py
│   │       ├── history_routes.py
│   │       ├── mcp_routes.py
│   │       ├── rollback_routes.py
│   │       ├── tasks_routes.py
│   │       ├── upload_routes.py
│   │       └── usage_routes.py
│   ├── sse/                         SSE 推送
│   │   ├── sse_queue.py
│   │   ├── sse_transport.py
│   │   └── terminal.py
│   ├── chat-server/                 Node.js 服务（不动）
│   └── web/                         前端（Vue + Vite）
│       ├── static/                  Vite 构建产物
│       └── static_vite/             前端源码（详见 folder-tree.md）
│
├── bootstrap/                        ★ 启动引导
│   ├── app_factory.py
│   ├── container.py
│   ├── settings.py
│   ├── lifecycle.py
│   └── logging.py
│
├── tests/
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
│   ├── e2e/
│   ├── fixtures/
│   ├── conftest.py
│   └── pytest.ini
│
├── scripts/                          ★ 运维脚本
│   ├── setup_env.py                 环境初始化
│   ├── setup_env.bat                Windows 入口
│   ├── setup_env.sh                 Linux/Mac 入口
│   ├── seed_data.py                 测试数据填充
│   └── migrate_db.py                数据库迁移
│
├── .codebuddy/
│   └── CODEBUDDY.md                  ★ AI 入口速查（自动注入）
├── .env.example                     环境变量模板
├── Makefile                         常用命令（dev/test/lint/docs/build）
├── mcp.json                         MCP 服务器配置
├── config.yaml                      运行时配置
├── pyproject.toml                   项目元数据 + Ruff 配置
├── Dockerfile                       应用容器化
├── docker-compose.yml               Docker Compose 编排
├── nginx.conf                       Nginx 反向代理
├── data/
│   └── conversations.db             统一数据库（自动生成）
├── asgi.py
├── __main__.py
└── dev.py
```

---

## 4. AI 友好三件套

为了最大化 AI（CodeBuddy）的工作效率和节省 token，采用三层结构设计：

### 4.1 `CODEBUDDY.md` —— 自动注入

CODEBUDDY.md 放在项目根目录 `.codebuddy/`，每次 AI 启动时自动加载。内容：
- 文件树大纲（顶层结构 + 关键模块简写）
- 依赖纪律（谁依赖谁）
- DDD Building Blocks 速查表
- import 路径示例

### 4.2 `__init__.py` + `__all__` —— import 时必读

每个包的 `__init__.py` 都要写 `__all__`。AI 在 import 时一定会读取 `__all__`，这是**零成本的信息传递通道**。

```python
# domain/__init__.py
from flypig.domain.session import Session
from flypig.domain.session_id import SessionId
from flypig.domain.session_status import SessionStatus
from flypig.domain.message import Message
from flypig.domain.message_id import MessageId
from flypig.domain.mode import Mode
from flypig.domain.persona import Persona
from flypig.domain.tool_call import ToolCall
from flypig.domain.tool_result import ToolResult
from flypig.domain.tool_def import ToolDefinition
from flypig.domain.change_score import ChangeScore
from flypig.domain.change_review import ChangeReview
from flypig.domain.suggestion_card import SuggestionCard
from flypig.domain.task_item import TaskItem
from flypig.domain.model_ref import ModelRef
from flypig.domain.exceptions import (
    FlyPigException, DomainError, SessionClosedError,
    InvalidTurnError, MessageValidationError,
    ConfigurationError, ModelAPIError, ToolExecutionError,
)

__all__ = [
    "Session", "SessionId", "SessionStatus",
    "Message", "MessageId",
    "Mode", "Persona",
    "ToolCall", "ToolResult", "ToolDefinition",
    "ChangeScore", "ChangeReview", "SuggestionCard",
    "TaskItem", "ModelRef",
    "FlyPigException", "DomainError", "SessionClosedError",
    "InvalidTurnError", "MessageValidationError",
    "ConfigurationError", "ModelAPIError", "ToolExecutionError",
]
```

### 4.3 文件顶部导航注释 —— 打开即见

每个 `.py` 文件的第一段注释不是 docstring 而是导航注释，格式固定：

```python
"""session: Session 聚合根

为什么做：AI Agent 需要一个有状态的生命周期对象来管理对话上下文、
         状态跃迁和消息集合。

实现方法：Session 是 DDD 聚合根，通过 transition_to() 保证状态机合法跃迁，
         通过 message_ids 引用下属 Message 实体。

实现效果：任何对 Session 的修改都经过聚合根方法，保证业务规则不被绕过。

层&amp;依赖：领域层 — 零外部依赖
细节见文档：docs/docs_refactor/ddd-architecture.md → §9.2
"""
```

格式严格遵守 5 段：
1. **一句话**：模块名 + 一句话职责
2. **为什么做**：需求场景，用户视角
3. **实现方法**：核心思路，1-3 句
4. **实现效果**：用户能感知的行为/体验变化
5. **层&依赖**：属于哪层 + 能依赖谁 + 不能依赖谁 + 细节见文档

---

## 5. 依赖方向（纪律声明）

```
domain/  ←  orchestration/  ←  infrastructure/  ←  interface/
  ↑                                   ↑
  |  └── ← 共享 shared/ 的基类        |
  └── → 直接实现 domain/ 逻辑（无接口层）
                bootstrap/
           （引导一切，不依赖业务逻辑）
```

### 具体规则

| 层 | 可以依赖 | 不能依赖 |
|----|---------|---------|
| `shared/` | Python 标准库、dataclasses、enum、ABC | 任何第三方库、任何业务层 |
| `domain/` | `shared/` 的基类、Python 标准库 | 第三方库（httpx, sqlite, openai）、`orchestration/`、`infrastructure/` |
| `orchestration/` | `domain/` 的值对象和实体（通过构造函数）、`shared/` | `infrastructure/` 的具体实现 |
| `acl/` | 第三方库、`shared/`、`domain/` exceptions | `orchestration/`（反向依赖） |
| `infrastructure/` | `domain/`、`shared/`、`acl/` | `orchestration/`（通过 DI 注入） |
| `interface/`（rest/sse） | `orchestration/` | `domain/` 的数据类可以直接用但不能创建 |
| `bootstrap/` | 所有层（DI 容器创建） | 业务逻辑 |
| `frontend/` | HTTP API / SSE | 后端 Python 模块 |

### import 检查点
如果看到以下情况，说明依赖方向错了：
- `from flypig.infrastructure.llm import OpenAIAdapter` 出现在 `domain/` 中
- `from flypig.orchestration.chat import ...` 出现在 `infrastructure/` 中
- 任何层依赖了 `interface/`（接口层只被 bootstrap/ 调用）
- `domain/` import 了 `shared/` 以外的包

---

## 6. 迁移映射（当前 → DDD）

当前 `flypig/` 的文件映射到新 DDD 结构：

| 当前目录 | DDD 新位置 | 操作说明 |
|---------|-----------|---------|
| `flypig/core/` | `flypig/bootstrap/` | core 改名为 bootstrap，内容拆分调整 |
| `flypig/core/config.py` | `flypig/bootstrap/settings.py` | 重命名 |
| `flypig/core/container.py` | `flypig/bootstrap/container.py` | 保留 |
| `flypig/core/app.py` | `flypig/bootstrap/app_factory.py` | 重命名 |
| `flypig/core/events.py` | `flypig/bootstrap/lifecycle.py` | 重命名 |
| `flypig/core/logging.py` | `flypig/bootstrap/logging.py` | 保留 |
| `flypig/domain/interfaces/` | `shared/` 基类 + `domain/*.py` | 接口定义扁平化为值对象/实体 |
| `flypig/domain/agent/state.py` | `flypig/orchestration/state.py` | 移至编排层 |
| `flypig/domain/agent/nodes.py` | `flypig/orchestration/nodes/` | 拆分子目录 |
| `flypig/domain/agent/context.py` | `flypig/orchestration/context.py` | 移至编排层 |
| `flypig/domain/agent/router.py` | `flypig/orchestration/graph.py` | 合并入 graph 定义 |
| `flypig/domain/models/message.py` | `flypig/domain/message.py` + `domain/tool_call.py` | 拍平到 domain/ |
| `flypig/domain/models/session.py` | `flypig/domain/session.py` + `domain/session_id.py` + ... | 拆成独立文件 |
| `flypig/domain/models/mode.py` | `flypig/domain/mode.py` | 拍平 |
| `flypig/domain/models/change_score.py` | `flypig/domain/change_score.py` + `domain/change_review.py` | 拆分 |
| `flypig/domain/config/` | `flypig/domain/model_ref.py` + `flypig/domain/pricing_entry.py` | 拍平 |
| `flypig/domain/prompts/` | `flypig/domain/persona.py` + 保留 prompt 文件 | 拍平值对象，roles 保留 |
| `flypig/domain/exceptions.py` | `flypig/domain/exceptions.py` | 保留，统一异常层次 |
| `flypig/backend/` | `flypig/interface/rest/` + `interface/sse/` | 重命名 |
| `flypig/backend/sse_queue.py` | `flypig/interface/sse/sse_queue.py` | 移至 SSE 子目录 |
| `flypig/backend/routes/` | `flypig/interface/rest/routes/` | 保留内容，移动位置 |
| `flypig/frontend/` | `flypig/interface/web/` | 重命名 |
| `flypig/orchestration/*` | `flypig/orchestration/*` | 保留，内容重组 |
| `flypig/infrastructure/*` | `flypig/infrastructure/*` + `flypig/acl/*` | 拆出 ACL 层 |
| `flypig/asgi.py` | 删除 | 逻辑并入 `__main__.py` |
| `flypig/dev.py` | 保留（根目录） | 不动 |

---

## 7. 值对象清单

| 值对象 | frozen | 位置 | 所属聚合 |
|--------|--------|------|---------|
| `SessionId` | ✓ | `domain/session_id.py` | Session |
| `MessageId` | ✓ | `domain/message_id.py` | Session |
| `Turn` | ✓ | `domain/turn.py` | Session |
| `Mode` | ✓ | `domain/mode.py` | Session |
| `Persona` | ✓ | `domain/persona.py` | Session |
| `ModeMatrix` | ✓ | `domain/mode_matrix.py` | — |
| `AgentState` | ✓ | `domain/agent_state.py` | — |
| `GraphSpec` | ✓ | `domain/graph_spec.py` | — |
| `ChatContext` | ✓ | `domain/chat_context.py` | Session |
| `ToolCall` | ✓ | `domain/tool_call.py` | Session |
| `ToolResult` | ✓ | `domain/tool_result.py` | Session |
| `ToolDefinition` | ✓ | `domain/tool_def.py` | — |
| `ChangeScore` | ✓ | `domain/change_score.py` | — |
| `ChangeReview` | ✓ | `domain/change_review.py` | — |
| `SuggestionCard` | ✓ | `domain/suggestion_card.py` | — |
| `ModelRef` | ✓ | `domain/model_ref.py` | — |
| `ApiKey` | ✓ | `domain/api_key.py` | — |
| `Workspace` | ✓ | `domain/workspace.py` | — |
| `PricingEntry` | ✓ | `domain/pricing_entry.py` | — |

### 实体清单

| 实体 | 身份标识 | 位置 | 说明 |
|------|---------|------|------|
| `Session` | `SessionId` | `domain/session.py` | 聚合根，核心生命周期对象 |
| `Message` | `MessageId` | `domain/message.py` | 下属实体，属于 Session 聚合 |
| `TaskItem` | `id`（str） | `domain/task_item.py` | 有状态机：pending → in_progress → completed |

### 值对象规范
- 所有值对象用 `@dataclass(frozen=True)`，禁止 setter
- 不具备唯一标识（即使有也隐藏在字段中）
- 相等性由所有字段共同决定
- 不可变性保证 AI 不会误修改共享数据
- tuple 代替 list，frozenset 代替 set

---

## 8. Bounded Context 地图

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Chat      │────>│    Agent     │────>│  Tool System  │
│ (interface/)│     │ (orchestratn)│     │ (infra/tools) │
└─────────────┘     └──────────────┘     └───────────────┘
       │                   │                     │
       v                   v                     v
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│ Execution   │────>│Configuration │     │   Pricing     │
│ (infra/)    │     │ (domain/)    │     │ (infra/pricng)│
└─────────────┘     └──────────────┘     └───────────────┘
```

### 通信规则

| 上下文 | 通信方式 | 中间层 |
|--------|---------|-------|
| Chat → Agent | REST/SSE → orchestration | `interface/rest/routes/chat_routes.py` |
| Agent → Tool System | ToolNode 路由 | `orchestration/tool.py` + `infrastructure/tools/executor.py` |
| Tool System → Execution | 命令下发 | 直接调用（同进程） |
| Agent → Configuration | 配置查询 | `orchestration/config.py` |
| Pricing → Agent | 事件订阅 | `orchestration/event_subscriptions.py` |
| LLM API → Agent | 防腐层翻译 | `acl/llm_api.py` |
| subprocess → Tool | 防腐层翻译 | `acl/subprocess.py` |

---

## 9. 代码示例

### 9.1 值对象定义

```python
# domain/session_id.py
from dataclasses import dataclass
from uuid import uuid4

@dataclass(frozen=True)
class SessionId:
    """会话 ID 值对象"""
    value: str

    @classmethod
    def generate(cls) -> "SessionId":
        return cls(value=uuid4().hex[:12])
```

```python
# domain/tool_call.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ToolCall:
    """工具调用请求值对象"""
    id: str
    name: str
    arguments: dict
```

### 9.2 实体 + 聚合根

```python
# domain/session.py
from dataclasses import dataclass, field
from datetime import datetime
from flypig.domain.session_id import SessionId
from flypig.domain.session_status import SessionStatus
from flypig.domain.message_id import MessageId
from flypig.domain.task_item import TaskItem

@dataclass
class Session:
    """会话实体 —— 有 ID，状态可变，是核心聚合根"""
    session_id: SessionId = field(default_factory=SessionId.generate)
    status: SessionStatus = SessionStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    # 下属实体通过 ID 引用（不直接嵌套）
    message_ids: list[MessageId] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    current_mode: str = "chat"
    metadata: dict = field(default_factory=dict)

    def transition_to(self, new_status: SessionStatus) -> None:
        """状态机跃迁 —— 聚合内保证不变条件"""
        allowed = {
            SessionStatus.IDLE: [SessionStatus.THINKING],
            SessionStatus.THINKING: [
                SessionStatus.WAITING_CHOICE,
                SessionStatus.EXECUTING,
                SessionStatus.REVIEWING,
                SessionStatus.ERROR,
            ],
            SessionStatus.WAITING_CHOICE: [SessionStatus.THINKING],
            SessionStatus.EXECUTING: [SessionStatus.REVIEWING, SessionStatus.ERROR],
            SessionStatus.REVIEWING: [SessionStatus.IDLE, SessionStatus.ERROR],
            SessionStatus.ERROR: [SessionStatus.IDLE],
        }
        if new_status not in allowed[self.status]:
            from flypig.domain.exceptions import DomainError
            raise DomainError(f"Invalid transition: {self.status} → {new_status}")
        self.status = new_status
        self.updated_at = datetime.now()
```

### 9.3 仓储接口 + 实现

```python
# shared/repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")

class Repository(ABC, Generic[T]):
    """仓储泛型接口 —— 领域层定义，基础设施层实现"""

    @abstractmethod
    async def get(self, id: str) -> T | None: ...

    @abstractmethod
    async def save(self, entity: T) -> None: ...

    @abstractmethod
    async def delete(self, id: str) -> None: ...
```

```python
# infrastructure/persistence/sqlite_session_repo.py
from flypig.shared.repository import Repository
from flypig.domain.session import Session
from flypig.domain.session_id import SessionId

class SqliteSessionRepository(Repository[Session]):
    """SQLite 实现的 Session 仓储"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get(self, id: str) -> Session | None: ...
    async def save(self, session: Session) -> None: ...
    async def delete(self, id: str) -> None: ...
```

### 9.4 DI 注入

```python
# bootstrap/container.py
from dependency_injector import containers, providers
from flypig.infrastructure.persistence.sqlite_session_repo import SqliteSessionRepository
from flypig.orchestration.chat import ChatService
from flypig.orchestration.session import SessionService

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # 仓储 —— 面向 `shared/repository.py` 接口编程
    session_repo = providers.Singleton(
        SqliteSessionRepository,
        db_path=config.db_path,
    )

    # 领域服务
    chat_service = providers.Factory(
        ChatService,
        session_repo=session_repo,
    )
    session_service = providers.Factory(
        SessionService,
        session_repo=session_repo,
    )
```

---

## 10. 迁移步骤

### Step 1：建共享内核和 ACL 层

| 动作 | 说明 |
|------|------|
| 创建 `shared/` | 从 `domain/interfaces/` 的基类抽象出 entity, aggregate_root, value_object, repository 等 |
| 创建 `acl/` | 从 `infrastructure/` 中拆出纯协议/错误翻译的文件 |
| 创建 `bootstrap/` | 从 `core/` 重命名迁移 |

### Step 2：拍平 domain/ 层

| 动作 | 说明 |
|------|------|
| `domain/models/message.py` → 拆 | Message 实体 + ToolCall/MessageId 值对象各成独立文件 |
| `domain/models/session.py` → 拆 | Session 实体 + SessionId/SessionStatus 值对象各成独立文件 |
| `domain/models/mode.py` → 拍平 | 变为 `domain/mode.py` |
| `domain/agent/` → 移出 | state/context 移入 `orchestration/`，nodes 移入 `orchestration/nodes/` |
| `domain/config/` → 拍平 | Config/ModelRegistry 变为 domain 层值对象 |
| `domain/interfaces/` → 归入 shared/ + domain | 抽象基类进 shared/，接口方法合并到实体 |

### Step 3：重命名目录

| 旧目录 | 新目录 |
|--------|-------|
| `flypig/core/` | `flypig/bootstrap/` |
| `flypig/backend/` | `flypig/interface/rest/` + `interface/sse/` |
| `flypig/frontend/` | `flypig/interface/web/` |

### Step 4：调整 import 路径

全部人力/AI 搜索替换，分轮次：

1. 第 1 轮：改 `flypig.core` → `flypig.bootstrap`
2. 第 2 轮：改 `flypig.backend` → `flypig.interface`
3. 第 3 轮：改 `flypig.domain.models` → `flypig.domain`
4. 第 4 轮：补全 `__init__.py` 的 `__all__` 导出
5. 第 5 轮：`python -c "import flypig"` 检查全部可导入

### Step 5：清理冗余

| 文件 | 操作 |
|------|------|
| `flypig/asgi.py` | 逻辑并入 `__main__.py` |
| `flypig/frontend/` → flypig/interface/web/ | 移动后删除旧路径 symlink |
| 空的 `__pycache__/` | 全部删除 |

---

## 11. 设计决策记录（ADR）

### ADR-001：为什么不用 CQRS/Event Sourcing

- **背景**: 讨论过是否引入完整的 CQRS 部署
- **决策**: 不引入
- **理由**: FlyPig 是单体 Agent 项目，不是金融交易系统。CQRS 和 Event Sourcing 引入的复杂度远大于收益
- **替代方案**: 如果未来需要审计日志，用简单的 append-only 表即可

### ADR-002：为什么 domain 拍平而非 Deep DDD 嵌套

- **背景**: 传统 DDD 鼓励 domain/ 内再按 aggregate 建子包
- **决策**: domain/ 拍平（最多 event/ 和 specification/ 两个子目录）
- **理由**: 拍平后 AI 更容易定位文件，减少"这文件放哪"的困惑
- **替代方案**: 如果某个聚合变得特别大（如 Session > 500 行），再拆出 `domain/session/` 子包

### ADR-003：为什么值对象每个类一个文件

- **背景**: 之前习惯相关类合并在一个文件
- **决策**: 每个值对象独立一个文件（`session_id.py`、`tool_call.py` 等）
- **理由**: AI 打开一个文件就能看到完整定义，不污染其他逻辑。值对象通常 <30 行，文件开销可忽略

### ADR-004：为什么不用抽象基类强制检查

- **背景**: 是否用 `ABCMeta` + `@abstractmethod` 强制子类实现所有接口方法
- **决策**: 用 ABC，但不强制（pure ABC 只做标记）
- **理由**: Python 的 ABC 运行时检查在 ASGI 项目中可能增加不必要的启动延迟和复杂度，标记接口意图即可
- **例外**: 如果高频出现"忘了实现某个接口方法"的 bug，再考虑启用

### ADR-005：为什么没有 domain/interfaces/ 目录

- **背景**: 传统 DDD 在 domain 层放 Interfaces 子目录
- **决策**: 接口定义直接位于使用它们的文件中（`shared/repository.py` 泛型）+ 实体/服务构造方法直接接受实现
- **理由**: Flat domain 减少 AI 导航层级。`shared/repository.py` 的泛型 Repository[T] 足以覆盖 90% 的仓储需求
- **例外**: 需要多实现的接口（如 IModel），接口放 `domain/model_ref.py` 旁边

### ADR-006：为什么单独拆出 ACL 层

- **背景**: 外部系统适配放在 Infrastructure 已足够
- **决策**: 单独 `acl/` 目录，拍平不嵌套
- **理由**: ACL 关注的是**协议转换 + 错误翻译**，不是基础设施实现。放在一起让 AI 混淆"这是实现还是适配"。独立目录后，每个外部系统一目了然

---

## 附录 A：值对象完整规范

```python
"""值对象规范

1. 所有值对象用 @dataclass(frozen=True)
2. 不具备唯一标识
3. 相等性由所有字段决定（默认 dataclass eq 行为）
4. 创建后不可修改
5. 不含业务逻辑（只有构造和转换方法）
6. 不可变保证：tuple 代替 list，frozenset 代替 set
"""
```

### 值对象清单（按文件）

**`domain/session_id.py`**
- `SessionId`: value（str）

**`domain/message_id.py`**
- `MessageId`: value（str）

**`domain/session_status.py`**
- `SessionStatus`: Enum（IDLE, THINKING, WAITING_CHOICE, EXECUTING, REVIEWING, ERROR）

**`domain/turn.py`**
- `Turn`: index（int）, role（Literal["user", "assistant", "tool"]）

**`domain/mode.py`**
- `Mode`: name（str）, allowed_tools（tuple）, requires_user_input（bool）, max_auto_turns（int）
- 预设：explore, plan, execute, review, teach

**`domain/persona.py`**
- `Persona`: name（str）, description（str）, system_prompt（str）

**`domain/tool_call.py`**
- `ToolCall`: id（str）, name（str）, arguments（dict）

**`domain/tool_result.py`**
- `ToolResult`: tool_call_id（str）, output（str）, error（str | None）

**`domain/tool_def.py`**
- `ToolDefinition`: name（str）, description（str）, parameters（dict）

**`domain/change_score.py`**
- `ChangeScore`: score（float）, line_count（int）, file_count（int）, complexity（str）, risk_level（str）

**`domain/change_review.py`**
- `ChangeReview`: score（ChangeScore）, passed（bool）, comments（tuple[str, ...]）

**`domain/suggestion_card.py`**
- `SuggestionCard`: title（str）, action（str）, params（dict）, explanation（str）

**`domain/model_ref.py`**
- `ModelRef`: name（str）, provider（str）, capabilities（tuple[str, ...]）

**`domain/api_key.py`**
- `ApiKey`: provider（str）, masked_key（str）, is_valid（bool）

**`domain/workspace.py`**
- `Workspace`: path（str）, name（str）, root（str）

**`domain/pricing_entry.py`**
- `PricingEntry`: model_name（str）, input_price（float）, output_price（float）, currency（str）, updated_at（str）

---

## 附录 B：Bounded Context 详细定义

| Bounded Context | 文件夹 | 核心概念 | 主要接口 | 所有者 |
|----------------|--------|---------|---------|-------|
| **Chat** | `interface/rest/` + `interface/web/` | 对话、SSE 事件流、工具调用展示 | `POST /api/chat` (SSE) | 后端+前端 |
| **Agent** | `orchestration/` + `orchestration/nodes/` | LangGraph 图、状态机、节点函数 | `orchestration/graph.py` | 后端 |
| **Tool System** | `infrastructure/tools/` | 工具注册、调用、审查、评分 | `infrastructure/tools/executor.py` | 后端 |
| **Execution** | `infrastructure/` (sandbox, system tools) | 文件操作、命令执行、Git 操作 | `acl/subprocess.py` | 后端 |
| **Configuration** | `domain/model_ref.py` + `domain/api_key.py` + `orchestration/config.py` | 模型、API Key、模式配置 | `orchestration/config.py` | 后端 |
| **Pricing** | `infrastructure/pricing/` + `domain/pricing_entry.py` | 价格获取、用量追踪 | `orchestration/pricing.py` | 后端 |

---

## 附录 C：文件夹树（当前旧 → DDD 新 映射速查）

> 用于 AI 快速定位：当前 `flypig/xxx.py` 应该放哪

```
当前旧位置                               → DDD 新位置
────────────────────────────────────────────────────────────
flypig/core/__init__.py                  → flypig/bootstrap/__init__.py
flypig/core/config.py                    → flypig/bootstrap/settings.py (重命名)
flypig/core/container.py                 → flypig/bootstrap/container.py
flypig/core/app.py                       → flypig/bootstrap/app_factory.py (重命名)
flypig/core/events.py                    → flypig/bootstrap/lifecycle.py (重命名)
flypig/core/logging.py                   → flypig/bootstrap/logging.py
flypig/domain/__init__.py                → flypig/domain/__init__.py (重写 __all__)
flypig/domain/interfaces/*.py            → flypig/shared/*.py (抽象基类)
flypig/domain/agent/state.py             → flypig/orchestration/state.py
flypig/domain/agent/nodes.py             → flypig/orchestration/nodes/*.py
flypig/domain/agent/context.py           → flypig/orchestration/context.py
flypig/domain/agent/router.py            → flypig/orchestration/graph.py
flypig/domain/models/session.py          → flypig/domain/session.py + session_id.py + session_status.py
flypig/domain/models/message.py          → flypig/domain/message.py + message_id.py + tool_call.py
flypig/domain/models/mode.py             → flypig/domain/mode.py
flypig/domain/models/change_score.py     → flypig/domain/change_score.py
flypig/domain/models/task.py             → flypig/domain/task_item.py
flypig/domain/config/config.py           → flypig/domain/model_ref.py + pricing_entry.py
flypig/domain/config/model_registry.py   → flypig/domain/model_ref.py (合并)
flypig/domain/prompts/                   → flypig/domain/persona.py + promps/ 内容保留
flypig/domain/exceptions.py              → flypig/domain/exceptions.py (扩展层次)
flypig/orchestration/*                   → flypig/orchestration/* (文件拆分重组)
flypig/infrastructure/llm/*              → flypig/infrastructure/llm/* + acl/llm_api.py
flypig/infrastructure/tools/*            → flypig/infrastructure/tools/* + acl/subprocess.py
flypig/infrastructure/executor.py        → flypig/infrastructure/tools/executor.py
flypig/infrastructure/search/*           → flypig/infrastructure/search/*
flypig/infrastructure/sandbox/*          → flypig/infrastructure/sandbox/* + acl/docker.py
flypig/infrastructure/policies/*         → flypig/infrastructure/policies/*
flypig/infrastructure/hooks.py           → flypig/infrastructure/hooks.py + acl/git.py
flypig/infrastructure/process_manager.py → flypig/infrastructure/process_manager.py
flypig/backend/__init__.py               → flypig/interface/rest/__init__.py
flypig/backend/routes/*.py               → flypig/interface/rest/routes/*.py
flypig/backend/sse_queue.py              → flypig/interface/sse/sse_queue.py
flypig/backend/terminal.py               → flypig/interface/sse/terminal.py
flypig/backend/file_watcher.py           → flypig/interface/rest/file_watcher.py
flypig/frontend/*                        → flypig/interface/web/*
flypig/asgi.py                           → 删除(并入 __main__.py)
flypig/config.yaml                       → 根目录(保留)
```

