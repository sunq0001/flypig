"""Quart 应用入口 + 路由注册

为什么做：所有 API 端点需要注册到 Quart 实例，并配置 CORS。

实现方法：create_app() 工厂函数，接收 Config 实例 → 注册蓝图（各路由模块各自管理）
→ CORS → 启动生命周期 → 返回 app。

实现效果：新增端点只需在对应蓝图文件加路由，server.py 只做装配。

技术栈：Quart, Blueprint, CORS

热加载验证：改此文件后 uvicorn --reload 会自动重启服务器
"""

from pathlib import Path

from quart import Quart
from quart_cors import cors

from domain.config.config import Config
from core.container import AppContainer


def create_app(config: Config | None = None) -> Quart:
    app = Quart(__name__)

    # 通过 DI 容器获取配置（也可直接传入覆盖）
    if config is None:
        container = AppContainer()
        app.config["flypig_container"] = container
        config = container.config()

    app.config["flypig_config"] = config

    # CORS（Vite proxy 在开发时处理跨域，生产用 nginx）
    app = cors(app, allow_origin="*")

    # 注册蓝图（各路由模块各自管理自己的端点）
    from backend.routes import config_bp, files_bp, health_bp, pricing_bp

    app.register_blueprint(config_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(pricing_bp)

    # 启动生命周期：定价缓存预热 + 每日刷新
    from infrastructure.usage.pricing import start_pricing_loop
    start_pricing_loop(app)

    return app
