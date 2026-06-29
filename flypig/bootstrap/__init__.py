"""FlyPig 应用骨架

为什么做：应用启动需要统一注册所有依赖和服务。

实现方法：bootstrap 包提供 Settings → Container → Logging → Lifecycle → App 的装配链路。

使用方式：from flypig.bootstrap import AppContainer, LifecycleEvents, create_app, load_config
"""

from flypig.bootstrap.settings import AppSettings, load_config
from flypig.bootstrap.container import AppContainer
from flypig.bootstrap.lifecycle import LifecycleEvents
from flypig.bootstrap.logging import init_logging
from flypig.bootstrap.app_factory import create_app
