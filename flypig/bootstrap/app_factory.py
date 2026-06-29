"""Quart App 工厂

为什么做：后端的 Web 入口需要统一创建 app 实例、注册蓝图、配置中间件。

实现方法：create_app() 工厂函数，先通过 load_config + AppContainer 初始化配置和 DI 容器，
再注册所有接口路由蓝图 + CORS + 日志中间件 + 生命周期事件。

实现效果：启动方式切换不影响路由代码，新增蓝图只需在工厂里加一行。

层&amp;依赖：bootstrap 层，依赖 interface/rest/routes 蓝图
"""

from __future__ import annotations

from pathlib import Path

from quart import Quart
from quart_cors import cors

from flypig.bootstrap.settings import AppSettings, load_config
from flypig.bootstrap.container import AppContainer
from flypig.bootstrap.lifecycle import LifecycleEvents
from flypig.bootstrap.logging import init_logging


def create_app(
    config_path: str | Path | None = None,
    settings: AppSettings | None = None,
) -> Quart:
    """创建并配置 Quart 应用实例"""
    if settings is None:
        settings = load_config(config_path)

    init_logging(level=settings.log_level)

    container = AppContainer()
    container.config.override(settings)

    app = Quart(__name__)
    app.config["flypig_settings"] = settings
    app.config["flypig_container"] = container

    app = cors(app, allow_origin="*")

    # 注册蓝图
    from flypig.interface.rest.routes.config_routes import config_bp
    from flypig.interface.rest.routes.files_routes import files_bp
    from flypig.interface.rest.routes.health_routes import health_bp
    from flypig.interface.rest.routes.chat_routes import chat_bp
    from flypig.interface.rest.routes.pricing_routes import pricing_bp

    app.register_blueprint(config_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(pricing_bp)

    events = LifecycleEvents()
    app.config["flypig_events"] = events

    @app.before_serving
    async def startup():
        await events.fire_startup()

    @app.after_serving
    async def shutdown():
        await events.fire_shutdown()

    return app
