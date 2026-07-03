"""Container — 依赖注入容器

为什么做：所有依赖（配置、模型、工具、存储、服务）需要统一注册和管理，
不能手动 new 或者从全局变量获取。模块间通过接口依赖，不直接引用实现。

实现方法：dependency-injector 声明式 DeclarativeContainer，各服务用 providers
声明作用域（Singleton/Factory），Wire 模式自动注入到模块。测试时 override 任意 provider。

实现效果：替换实现只需改一行绑定，测试时 override 任意依赖，新增服务只需加一行 provider。

层&amp;依赖：bootstrap 层（胶水代码）
"""

from dependency_injector import containers, providers

from flypig.domain.registry import ModelRegistry
from flypig.infrastructure.llm.model_factory import ModelFactory
from flypig.infrastructure.usage.pricing import PricingService
from flypig.application.chat_service import ChatApplicationService


class AppContainer(containers.DeclarativeContainer):
    """应用依赖注入容器"""

    config = providers.Configuration()

    # ── 域服务 ──
    model_registry = providers.Singleton(ModelRegistry)

    # ── 基础设施 ──
    model_factory = providers.Factory(
        ModelFactory,
        registry=model_registry,
    )
    pricing_service = providers.Singleton(
        PricingService,
        registry=model_registry,
    )

    # ── 应用服务 ──
    chat_service = providers.Factory(
        ChatApplicationService,
        model_factory=model_factory,
        settings=config,
    )
