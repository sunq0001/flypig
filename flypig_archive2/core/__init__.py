"""FlyPig 应用骨架

为什么做：应用启动需要统一注册所有依赖和服务，不能散落在各处手动 new。
实现方法：core 包提供 Settings → Container → Logging → Events → App 的装配链路，所有模块通过 DI 容器获取依赖。
实现效果：启动流程规范统一，换配置/换模型只需要改一处。
技术栈：pydantic-settings, dependency-injector, loguru, Quart, PyYAML

层&依赖：core 层（胶水代码），依赖 domain 接口 + infrastructure 实现 + orchestration 服务 + backend 路由
细节见文档：docs/docs_refactor/architecture-guide.md → §重构动机

使用方式：from core import AppContainer, LifecycleEvents, create_app, load_config
"""

from .settings import AppSettings, load_config
from .container import AppContainer
from .events import LifecycleEvents
from .logging import init_logging
from .app import create_app
