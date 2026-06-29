"""Quart App 工厂

为什么做：后端的 Web 入口需要统一创建 app 实例、注册蓝图、配置中间件，不能在 __main__.py 里内联写死。

实现方法：create_app() 工厂函数，先通过 load_config + AppContainer 初始化配置和 DI 容器，
再注册所有后端路由蓝图 + CORS + 日志中间件 + 生命周期事件。

实现效果：启动方式切换（dev/prod）不影响路由代码，新增蓝图只需在工厂里加一行。

技术栈：Quart, CORS, SSE, Loguru

层&依赖：core 层，依赖 backend/routes 蓝图 + infrastructure 中间件
细节见文档：docs/docs_refactor/backend-modules.md → §Backend Layer、data-flow.md → §后端数据流、tech-stack.md → §Web 框架
"""

from __future__ import annotations

from pathlib import Path

from quart import Quart
from quart_cors import cors

from core.settings import AppSettings, load_config
from core.container import AppContainer
from core.events import LifecycleEvents
from core.logging import init_logging


def create_app(
    config_path: str | Path | None = None,
    settings: AppSettings | None = None,
) -> Quart:
    """创建并配置 Quart 应用实例

    Args:
        config_path: config.yaml 路径，默认 flypig/config.yaml
        settings: 可选外部传入配置，用于测试覆盖
    """
    # 1. 加载配置
    if settings is None:
        settings = load_config(config_path)

    # 2. 初始化日志
    init_logging(level=settings.log_level)

    # 3. 创建 DI 容器
    container = AppContainer()
    container.config.override(settings)

    # 4. 创建 app
    app = Quart(__name__)
    app.config["flypig_settings"] = settings
    app.config["flypig_container"] = container

    # 5. CORS
    app = cors(app, allow_origin="*")

    # 6. 注册蓝图
    from backend.routes.config import config_bp
    from backend.routes.files import files_bp

    app.register_blueprint(config_bp)
    app.register_blueprint(files_bp)

    # 7. 生命周期
    events = LifecycleEvents()
    app.config["flypig_events"] = events

    @app.before_serving
    async def startup():
        await events.fire_startup()

    @app.after_serving
    async def shutdown():
        await events.fire_shutdown()

    # 8. 内置路由
    @app.route("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.route("/api/ping")
    async def ping():
        return {"pong": True}

    return app
