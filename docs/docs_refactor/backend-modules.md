# 后端模块

> **来源**: `architecture-refactor.md` §3.1-3.5, §3.10
> **关联文档**: `langgraph-graph.md`（AgentState）、`subprocess-and-tools.md`（工具执行）、`usage-tracking.md`（用量追踪）

## Interface Layer — 用户界面适配

```
flypig/interface/web/
├── server.py           # app 声明 + 路由注册（~50 行）
├── routes/
│   ├── chat.py         # /api/chat SSE 端点（≤120 行）
│   ├── config.py       # /api/config/*（≤80 行）
│   ├── files.py        # /api/files, /api/file, /api/tree（≤80 行）
│   ├── sessions.py     # 历史会话路由
│   ├── health.py       # 健康检查
│   ├── upload.py       # 文件上传 + 压缩解压
│   ├── rollback.py     # Git 回滚
│   ├── agent.py        # /api/agent/status + /api/agent/stop
│   ├── history.py      # /api/history/search
│   ├── usage.py        # /api/usage/*（用量查询）
│   └── feedback.py     # /api/feedback/suggestion（建议反馈记录）
└── services/
    ├── sse_queue.py    # SSE 队列抽象（≤40 行）
    └── file_watcher.py # 文件变更监控（≤50 行）
```

## Application Layer — 业务编排

| 服务 | 职责 | 行数 |
|------|------|------|
| `ChatService` | 接收输入 → 调用 LangGraph → 事件分发 | ≤60 |
| `ConfigService` | Config 初始化、模型切换、API Key 管理 | ≤80 |
| `SessionService` | 多会话创建/切换/销毁/持久化 + `restore()` 恢复断点 | ≤100 |
| `PolicyService` | Casbin 封装 | ≤80 |
| `GraphFactory` | ★ 图构建：导入 nodes + router → 编译 StateGraph（原 OrchestrationService.build_graph()） | ≤80 |
| `SuggestionEngine` | ★ 评分→建议映射：generate_suggestion()（原 OrchestrationService 拆分） | ≤40 |
| `HookService` | ★ 钩子管理器：register(event_type, hook) / emit(event_type, data) | ≤40 |
| `GitCheckpointManager` | ★ Agent Git checkpoints 管理（init/commit/restore） | ≤80 |
| `CheckpointStore` | ★ SQLite 映射表（turn_id → commit_hash → summary） | ≤60 |
| `SummaryGenerator` | ★ 根据本轮交互生成 ≤50 字摘要 | ≤40 |
| `UsageTrackerService` | ★ 用量追踪：通过 HookService 自动记录 turn/call 级 token、cost、缓存 | ≤60 |

## Domain Layer — 核心领域逻辑

```
flypig/domain/
├── interfaces/         # IModel, IToolExecutor, IHook+HookContext, IHistoryStore
├── agent/              # state.py, nodes.py, router.py, context.py（领域层只定义逻辑）
├── models/             # Message, Session, ChangeScore, ExecutionMode
├── prompt_manager.py   # 多角色 prompt 懒加载
├── prompts/            # developer.md, reviewer.md, tester.md, architect.md, documenter.md
├── policies/           # Casbin 权限定义
├── exceptions.py       # 统一异常
└── config/             # config.py, model_registry.py
```

## Infrastructure Layer — 基础设施

```
├── model/              # openai_adapter.py, anthropic.py, local.py
├── tools/              # executor.py + edit/search/system/mcp 四组（详见 folder-tree.md）
├── sandbox/            # config, path_validator, manager, builder
├── usage/              # ★ IUsageTracker（取代原 ICostTracker）+ SqliteUsageTracker + PricingFetcher + UsageTrackerHook
├── repository/         # SQLAlchemy + IHistoryStore NoOp
├── policies/           # Casbin（model.conf + policy.csv + setup）
├── terminal.py         # 用户手动 PTY（精简版，无 AI 注入）
├── hooks.py            # HookService 的具体实现（log / sse_push / notification 等）
└── background.py       # 后台任务管理
```

## 模型适配

国产模型优先（DeepSeek、Qwen、GLM、Yi、Baichuan），均兼容 OpenAI API 格式：

```
infrastructure/model/
├── openai_adapter.py   # OpenAI/DeepSeek 兼容（当前主力）
├── anthropic.py        # Claude 适配
└── local.py            # 本地模型（Ollama/vLLM，预留）
```

## 配置即代码（Config as Code）

模型配置不应硬编码，建议用 YAML + 数据类分离配置与代码：

```yaml
# model_registry.yaml
models:
  deepseek:
    provider: openai-compatible
    base_url: https://api.deepseek.com
    default_model: deepseek-chat
    temperature: { explore: 0.1, plan: 0.2, execute: 0.3 }
  qwen:
    provider: openai-compatible
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
```

```python
@dataclass
class ModelConfig:
    provider: str
    base_url: str
    default_model: str
    temperature: dict

class Config:
    def __init__(self, path="config.yaml"):
        raw = yaml.safe_load(Path(path).read_text())
        self.models = {k: ModelConfig(**v) for k, v in raw["models"].items()}
```

## 数据类型规范

所有跨层传递的数据用 `@dataclass` 替代 `dict`，函数签名自文档化，IDE 自动补全：

```python
# 避免: def ask_choice(...) -> dict:  # 返回什么？要读实现
# 采用: def ask_choice(...) -> ChoiceCard:  # 返回类型说明一切

@dataclass
class ChoiceCard:
    id: str
    question: str
    options: list[Option]
    multi_select: bool = False

@dataclass
class Option:
    label: str
    desc: str
    value: str
```

同样适用于 ChangeReview、ChangeScore 等所有返回 `dict` 的接口。

## DI Container

```python
class Container:
    """依赖注入容器，单点装配所有依赖"""

    _instances = {}

    @classmethod
    def configure(cls, env="web"):
        """一劳永逸地装配所有依赖"""
        config = Config()
        model = ModelAdapter(config.default_model)      # 实现 IModel
        tools = ToolExecutor(workspace_dir=config.workspace)  # 实现 IToolExecutor
        repo = SqliteConversationStore("data/conversations.db")  # 实现 IConversationStore
        policy = PolicyService(config.permissions)      # 权限规则
        prompts = PromptManager()                       # 多角色 prompt
        knowledge = NoOpKnowledgeStore()                # 知识库空实现
        graph_factory = GraphFactory(
            tools=tools, prompts=prompts, policy=policy
        )
        suggestion_engine = SuggestionEngine()
        hook_service = HookService()

        # ★ 记忆 + 压缩体系
        conversation_store = SqliteConversationStore("data/conversations.db")
        context_pipeline = CompositePipeline(layers=[
            TruncateResultsLayer(max_result_len=2000),
            FoldOldTurnsLayer(max_complete_turns=15),
            TrimMessagesLayer(budget=100_000),
        ])

        cls.register("config", config, singleton=True)
        cls.register("model", model, singleton=True)
        cls.register("tools", tools, singleton=True)
        cls.register("repository", repo, singleton=True)
        cls.register("policy", policy, singleton=True)
        cls.register("prompts", prompts, singleton=True)
        cls.register("knowledge_store", knowledge, singleton=True)
        cls.register("graph_factory", graph_factory, singleton=True)
        cls.register("suggestion_engine", suggestion_engine, singleton=True)
        cls.register("hook_service", hook_service, singleton=True)
        cls.register("conversation_store", conversation_store, singleton=True)
        cls.register("context_pipeline", context_pipeline, singleton=True)

        # ★ 用量追踪
        usage_tracker = SqliteUsageTracker("data/usage.db")   # 实现 IUsageTracker
        pricing_fetcher = PricingFetcher()
        usage_hook = UsageTrackerHook(usage_tracker, pricing_fetcher)
        cls.register("usage_tracker", usage_tracker, singleton=True)
        cls.register("pricing_fetcher", pricing_fetcher, singleton=True)

    @classmethod
    def create_agent(cls, workspace=None, hooks=None) -> "IAgent":
        """创建 Agent 实例（返回 IAgent 接口）"""
        return Agent(
            model=cls.get("model"),
            cost_tracker=cls.get("cost_tracker"),
            tools=cls.get("tools"),
            system_prompt=_build_prompt(workspace),
            hooks=hooks,
        )

    @classmethod
    def register(cls, name, instance, singleton=False): ...
    @classmethod
    def get(cls, name): ...
```

## 健壮性

### 环形缓冲区防内存泄漏

```python
from collections import deque
_BUFFER_MAX_LINES = 10000
_BACKGROUND_PROCESSES[pid]["buffer"] = deque(maxlen=_BUFFER_MAX_LINES)
```

后台进程空闲超 1 小时自动销毁，Agent reset 时 kill 关联进程。

### 统一异常

```python
class FlyPigException(Exception): pass
class ConfigurationError(FlyPigException): pass
class ModelAPIError(FlyPigException): pass
class ToolExecutionError(FlyPigException): pass
class SandboxError(FlyPigException): pass
```

### 超时分级

```python
_TOOL_TIMEOUTS = {"read_file": 5, "bash": 30, "grep": 30, "write_file": 10}
```

### 健康检查

```python
@app.route("/health")
@app.route("/ready")
```

### 断路器（Circuit Breaker）

模型 API 连续失败时自动熔断，防止级联故障：

```python
@dataclass
class CircuitBreakerState:
    failure_count: int = 0
    last_failure_time: float = 0
    is_open: bool = False               # 熔断开启
    half_open_attempts: int = 0

_CIRCUIT_BREAKERS: dict[str, CircuitBreakerState] = {}

def circuit_breaker(name: str, failure_threshold=5, recovery_timeout=60):
    """装饰器：API 调用连续失败 threshold 次后熔断 recovery_timeout 秒"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            state = _CIRCUIT_BREAKERS.setdefault(name, CircuitBreakerState())
            if state.is_open:
                elapsed = time.time() - state.last_failure_time
                if elapsed < recovery_timeout:
                    raise CircuitBreakerError(f"{name} 熔断中，剩余 {recovery_timeout - elapsed:.0f}s")
                state.is_open = False  # 尝试半开
            try:
                result = await func(*args, **kwargs)
                state.failure_count = 0
                return result
            except Exception as e:
                state.failure_count += 1
                state.last_failure_time = time.time()
                if state.failure_count >= failure_threshold:
                    state.is_open = True
                raise
        return wrapper
    return decorator

class CircuitBreakerError(FlyPigException): pass
```

使用场景：`IModel.chat_stream()` 外层加 `@circuit_breaker("chat_stream", failure_threshold=5, recovery_timeout=60)`。

### 重试机制（Retry）

工具执行因网络抖动/临时资源不足失败时自动重试：

```python
async def retry(func, max_retries=2, backoff=1.0, retryable_exceptions=(TimeoutError, ConnectionError)):
    """重试装饰器：指数退避重试"""
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retryable_exceptions as e:
            if attempt == max_retries:
                raise
            await asyncio.sleep(backoff * (2 ** attempt))
```

使用场景：`tool_bash.py` 的 subprocess 执行、`tool_file.py` 的文件写入。

### 监控（Metrics）

生产环境通过 Prometheus 暴露性能指标：

| 指标 | 类型 | 说明 |
|------|------|------|
| `flypig_requests_total` | Counter | 总请求数，按 endpoint/status 标记 |
| `flypig_request_duration_seconds` | Histogram | 请求延迟分布 |
| `flypig_tool_calls_total` | Counter | 工具调用次数，按 tool/mode 标记 |
| `flypig_llm_tokens_total` | Counter | LLM token 消耗，按 model 标记 |
| `flypig_circuit_breaker_state` | Gauge | 断路器状态（0=关闭, 1=开启, 2=半开） |

```python
# application/services/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

requests_total = Counter("flypig_requests_total", "Total requests", ["endpoint", "status"])
request_duration = Histogram("flypig_request_duration_seconds", "Request latency", ["endpoint"])
tool_calls_total = Counter("flypig_tool_calls_total", "Tool calls", ["tool", "mode"])
llm_tokens_total = Counter("flypig_llm_tokens_total", "LLM tokens", ["model"])
circuit_breaker_state = Gauge("flypig_circuit_breaker_state", "Circuit breaker state", ["name"])
```

暴露端点：`/metrics`（由 prometheus_client 自动提供）。

### SQLite WAL 模式

LangGraph Checkpointer + ConversationStore 都使用 SQLite。多会话并发写入时，默认模式会锁表。

```python
# Checkpointer 初始化
SqliteSaver.from_conn_string("langgraph.db?mode=wal")

# ConversationStore 初始化
engine = create_async_engine("sqlite+aiosqlite:///conversations.db?mode=wal")
```

### 全局 trace_id

用 `trace_id = f"{session_id}_{turn_id}"` 串联所有日志行和工具调用：

```python
# chat_node 中生成
trace_id = f"{state['session_id']}_{state['turn_id']}"

# 所有日志、工具调用、SSE 事件都带上
logging.info("[trace=%s] 用户输入: %s", trace_id, user_input)
logging.info("[trace=%s] tool_call: %s(%s)", trace_id, tool_name, args)
```

| ID | 格式 | 生命周期 |
|----|------|---------|
| `trace_id` | `session_id_turn_id` | 一轮对话内所有操作共享 |
| `span_id` | `trace_id_tool_index` | 每轮内每次工具调用独立 |

等上 OpenTelemetry 时，直接映射为 OTEL trace_id / span_id。

### 优雅关闭

LangGraph Checkpointer 持久化的是**上一轮完成后**的状态。如果进程被 SIGTERM 杀死（docker restart、部署更新），正在执行的工具调用会丢失结果。

**当前 MVP 阶段**：不处理，重启后用户重试即可。

**SaaS 阶段**：以下表追踪工具执行状态：

```sql
CREATE TABLE tool_executions (
    execution_id TEXT PRIMARY KEY,
    session_id TEXT,
    turn_id INTEGER,
    tool_name TEXT,
    status TEXT,           -- running / completed / failed / timeout
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

### 敏感信息检测

LLM 输出可能包含 API key、密码等敏感字符串。在 `chat_node` 返回前端前做检测：

```python
import re

_SENSITIVE_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', "API Key（sk- 开头）"),
    (r'AIza[0-9A-Za-z\-_]{35}', "Google API Key"),
    (r'password\s*[:=]\s*["\']?[\w!@#$%^&*]+', "密码赋值"),
    (r'-----BEGIN (RSA |EC )?PRIVATE KEY-----', "私钥"),
]

def detect_sensitive(content: str) -> list[dict]:
    matches = []
    for pattern, name in _SENSITIVE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            matches.append({"type": name, "pattern": pattern})
    return matches
```

检测结果不拦截内容，改为在前端标黄警告：
- 前端 `MessageItem.vue` 检测到 `has_sensitive` 字段 → 消息上方加⚠️横幅
- 不改内容，不替换，不自动删除
- LLM 编码场景下读写密码是正常操作，设计上不能过度拦截

```python
# chat_node 返回时
sensitive = detect_sensitive(response.content)
if sensitive:
    response.additional_kwargs["has_sensitive"] = True
    response.additional_kwargs["sensitive_items"] = sensitive
```

## 中介者模式：ChatService

`ChatService` 天然承担了中介者角色——它协调 `GraphFactory`、`HookService`、`SuggestionEngine`、`PolicyService` 之间的交互，但这些服务之间互不知晓对方存在：

```python
class ChatService:
    """中介者：协调所有服务的交互"""

    def __init__(self):
        self.graph_factory = Container.get("graph_factory")
        self.hook_service = Container.get("hook_service")
        self.suggestion_engine = Container.get("suggestion_engine")
        self.policy = Container.get("policy")
        self.repository = Container.get("repository")

    async def process_message(self, user_msg: str, session_id: str) -> AsyncGenerator:
        """五步流程，中介者统一编排"""
        # Step 1: 权限检查
        if not await self.policy.can_chat(session_id):
            yield PolicyBlocked()
            return

        # Step 2: 触发前置事件（中介者通知 HookService）
        await self.hook_service.emit("chat:before", {
            "session_id": session_id, "message": user_msg
        })

        # Step 3: 获取/构建 Graph（中介者协调 GraphFactory）
        graph = self.graph_factory.build_graph(session_id)

        # Step 4: 执行并生成建议（中介者协调 SuggestionEngine）
        async for event in graph.astream_events({"messages": [user_msg]}):
            if event["type"] == "on_suggestion":
                suggestion = await self.suggestion_engine.generate(event["data"])
                yield suggestion
            else:
                yield event

        # Step 5: 触发完成事件
        await self.hook_service.emit("chat:after", {"session_id": session_id})

# 各服务之间没有任何直接引用：
# GraphFactory 不知道 HookService 存在
# SuggestionEngine 不知道 PolicyService 存在
# 新增服务只需加一行 self.xxx = Container.get("xxx") + 在 process_message 中编排
```

**效果**：新增一个服务时，只需改 `ChatService` 一个类，其他服务不需做任何修改。

## 建造者模式：AgentBuilder（预留）

当前 `Container.create_agent()` 的参数不多（`workspace`、`hooks`），直接作为类方法够用。但未来若新增参数（`sandbox_config`、`custom_tool_list`、`prompt_overrides`），建议用建造者模式避免构造函数爆炸：

```python
class AgentBuilder:
    """建造者模式：一步步配置 Agent（参数超过 8 个时启用）"""

    def __init__(self):
        self._hooks = []
        self._workspace = None
        self._tools = None
        self._prompt_file = None
        self._sandbox_enabled = False
        self._sandbox_config = {}
        self._max_iterations = 20
        self._knowledge_bases = []

    def with_workspace(self, path: str) -> "AgentBuilder":
        self._workspace = path
        return self

    def with_hooks(self, hooks: list) -> "AgentBuilder":
        self._hooks = hooks
        return self

    def with_tools(self, tools: list[str]) -> "AgentBuilder":
        """限制 Agent 可用工具列表"""
        self._tools = tools
        return self

    def with_sandbox(self, config: dict | None = None) -> "AgentBuilder":
        self._sandbox_enabled = True
        if config:
            self._sandbox_config = config
        return self

    def with_knowledge(self, knowledge_bases: list) -> "AgentBuilder":
        self._knowledge_bases = knowledge_bases
        return self

    def with_max_iterations(self, n: int) -> "AgentBuilder":
        self._max_iterations = n
        return self

    async def build(self) -> "IAgent":
        """最后一步才创建，参数校验统一在这里"""
        if not self._workspace:
            raise ValueError("Agent 必须指定 workspace")

        model = Container.get("model")
        tools = self._tools or await Container.get("tools").get_available_tools()

        return Agent(
            model=model,
            tools=tools,
            hooks=self._hooks,
            workspace=self._workspace,
            sandbox=SandboxConfig(**self._sandbox_config) if self._sandbox_enabled else None,
            max_iterations=self._max_iterations,
            knowledge_bases=self._knowledge_bases,
        )

# 使用
agent = await (AgentBuilder()
    .with_workspace("/var/www/stock")
    .with_hooks([LogHook(), SsePushHook()])
    .with_tools(["bash", "file", "search", "mcp_*"])
    .with_sandbox({"memory": "512m", "timeout": 60})
    .with_max_iterations(50)
    .build())
```

**何时启用**：`Container.create_agent()` 的命名参数超过 **8 个**时，切换到 AgentBuilder。在此之前保持现状即可。

> **关联文档**: `adversarial-system.md`（对抗审核）、`langgraph-graph.md`（AgentState）
