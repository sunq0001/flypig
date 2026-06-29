"""Container — 依赖注入容器

为什么做：所有依赖（配置、模型、工具、存储、服务）需要统一注册和管理，
不能手动 new 或者从全局变量获取。模块间通过接口依赖，不直接引用实现。

实现方法：dependency-injector 声明式 DeclarativeContainer，各服务用 providers
声明作用域（Singleton/Factory），Wire 模式自动注入到模块。测试时 override 任意 provider。

实现效果：替换实现只需改一行绑定，测试时 override 任意依赖，新增服务只需加一行 provider。

层&amp;依赖：bootstrap 层（胶水代码）
"""

from dependency_injector import containers, providers


class AppContainer(containers.DeclarativeContainer):
    """应用依赖注入容器"""

    config = providers.Configuration()

    # ── 后续逐步添加 ──
    # model         = providers.Singleton(OpenAIAdapter, api_key=config.provided.api_key)
    # tools         = providers.Singleton(ToolExecutor, workspace=config.provided.workspace)
    # conversation  = providers.Singleton(SqliteConversationStore)
    # policy        = providers.Singleton(PolicyService)
    # prompts       = providers.Singleton(MultiRoleManager)
    # graph_factory = providers.Singleton(GraphFactory, tools=tools, prompts=prompts)
    # suggestion    = providers.Singleton(SuggestionEngine)
    # events        = providers.Singleton(EventSubscriptions)
    # usage_tracker = providers.Singleton(SqliteUsageTracker)
