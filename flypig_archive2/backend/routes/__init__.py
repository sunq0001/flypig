"""后端路由蓝图

使用方式：from backend.routes import config_bp, files_bp, health_bp, pricing_bp, chat_bp
"""

from .chat import chat_bp
from .config import config_bp
from .files import files_bp
from .health import health_bp
from .pricing import pricing_bp
