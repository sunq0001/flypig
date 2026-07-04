"""__init__

为什么做：引导层负责应用启动时装配所有依赖和服务

实现方法：Settings → Container → Logging → Lifecycle → App 的工厂链路

层&依赖：bootstrap 层
"""

from flypig.shared.settings import AppSettings
from flypig.bootstrap.settings import load_config
from flypig.bootstrap.container import AppContainer
from flypig.bootstrap.lifecycle import LifecycleEvents
from flypig.bootstrap.logging import init_logging
from flypig.bootstrap.app_factory import create_app

__all__ = [
    "AppContainer",
    "AppSettings",
    "LifecycleEvents",
    "create_app",
    "init_logging",
    "load_config",
]
