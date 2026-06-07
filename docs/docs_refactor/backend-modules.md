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
| `ChatService` | 接收输入 → 调用 LangGraph → 事件回调 | ≤60 |
| `ConfigService` | Config 初始化、模型切换、API Key 管理 | ≤80 |
| `SessionService` | 多会话创建/切换/销毁/持久化 | ≤80 |
| `OrchestrationService` | 图构建 + 对抗建议 + build_graph() | ≤100 |

## Domain Layer — 核心领域逻辑

```
flypig/domain/
├── interfaces/         # IModel, IToolExecutor, ICostTracker, IHook, IHistoryStore
├── agent/              # graph.py, nodes.py, router.py, context.py（统一图）
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
├── tools/              # 全部工具（详见 subprocess-and-tools.md）
├── sandbox/            # config, path_validator, manager, builder
├── cost/               # CostTracker + pricing
├── repository/         # SQLAlchemy + IHistoryStore NoOp
├── policies/           # Casbin（model.conf + policy.csv + setup）
├── terminal.py         # 用户手动 PTY（精简版，无 AI 注入）
├── hooks.py            # 事件钩子
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
        orchestration = OrchestrationService(
            model=model, prompts=prompts, policy=policy
        )
        cls.register("config", config, singleton=True)
        cls.register("model", model, singleton=True)
        cls.register("cost_tracker", cost_tracker, singleton=True)
        cls.register("tools", tools, singleton=True)
        cls.register("repository", repo, singleton=True)
        cls.register("policy", policy, singleton=True)
        cls.register("prompts", prompts, singleton=True)
        cls.register("knowledge_store", knowledge, singleton=True)
        cls.register("history_store", NoOpHistoryStore(), singleton=True)
        cls.register("orchestration", orchestration, singleton=True)

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
