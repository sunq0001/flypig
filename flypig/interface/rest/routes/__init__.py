"""接口路由蓝图

使用方式：from flypig.interface.rest.routes import config_bp, files_bp, ...
"""

from flypig.interface.rest.routes.config_routes import config_bp
from flypig.interface.rest.routes.files_routes import files_bp
from flypig.interface.rest.routes.health_routes import health_bp
from flypig.interface.rest.routes.pricing_routes import pricing_bp
from flypig.interface.rest.routes.chat_routes import chat_bp
