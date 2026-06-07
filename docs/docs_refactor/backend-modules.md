# 后端模块

> **来源**: `architecture-refactor.md` §3.1-3.5, §3.10
> **关联文档**: `langgraph-graph.md`（AgentState）、`subprocess-and-tools.md`（工具执行）

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
│   └── rollback.py     # Git 回滚
└── services/
    ├── sse_queue.py    # SSE 队列抽象（≤40 行）
    └── file_watcher.py # 文件变更监控（≤50 行）
```

## Application Layer — 业务编排

| 服务 | 职责 | 行数 |
|------|------|------|
| `ChatService` | 接收输入 → 调用 LangGraph → 事件分发 | ≤60 |
| `ConfigService` | Config 初始化、模型切换、API Key 管理 | ≤80 |
| `SessionService` | 多会话创建/切换/销毁/持久化 | ≤80 |
| `PolicyService` | Casbin 封装 | ≤80 |
| `GraphFactory` | ★ 图构建：导入 nodes + router → 编译 StateGraph（原 OrchestrationService.build_graph()） | ≤80 |
| `SuggestionEngine` | ★ 评分→建议映射：generate_suggestion()（原 OrchestrationService 拆分） | ≤40 |
| `HookService` | ★ 钩子管理器：register(event_type, hook) / emit(event_type, data) | ≤40

## Domain Layer — 核心领域逻辑

```
flypig/domain/
├── interfaces/         # IModel, IToolExecutor, ICostTracker, IHook+HookContext, IHistoryStore
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
├── cost/               # CostTracker + pricing
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
        cost_tracker = CostTracker(config.pricing_dict) # 实现 ICostTracker
        tools = ToolExecutor(workspace_dir=config.workspace)  # 实现 IToolExecutor
        repo = SqliteRepository(config.db_path)         # 实现 IRepository
        policy = PolicyService(config.permissions)      # 权限规则
        prompts = PromptManager()                       # 多角色 prompt
        knowledge = NoOpKnowledgeStore()                # 知识库空实现
        graph_factory = GraphFactory(
            tools=tools, prompts=prompts, policy=policy
        )
        suggestion_engine = SuggestionEngine()
        hook_service = HookService()
        cls.register("config", config, singleton=True)
        cls.register("model", model, singleton=True)
        cls.register("cost_tracker", cost_tracker, singleton=True)
        cls.register("tools", tools, singleton=True)
        cls.register("repository", repo, singleton=True)
        cls.register("policy", policy, singleton=True)
        cls.register("prompts", prompts, singleton=True)
        cls.register("knowledge_store", knowledge, singleton=True)
        cls.register("history_store", NoOpHistoryStore(), singleton=True)
        cls.register("graph_factory", graph_factory, singleton=True)
        cls.register("suggestion_engine", suggestion_engine, singleton=True)
        cls.register("hook_service", hook_service, singleton=True)

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
