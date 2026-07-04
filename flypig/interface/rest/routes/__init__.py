"""__init__

为什么做：统一导出所有 API 路由蓝图

实现方法：集中 import + __all__，注册到 Quart app

层&依赖：interface.rest.routes 层
"""

from flypig.interface.rest.routes.config_routes import config_bp
from flypig.interface.rest.routes.files_routes import files_bp
from flypig.interface.rest.routes.health_routes import health_bp
from flypig.interface.rest.routes.pricing_routes import pricing_bp
from flypig.interface.rest.routes.chat_routes import chat_bp

__all__ = [
    "chat_bp",
    "config_bp",
    "files_bp",
    "health_bp",
    "pricing_bp",
]
