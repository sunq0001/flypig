"""app_factory

为什么做：后端的 Web 入口需要统一创建 app 实例、注册蓝图、配置中间件

实现方法：create_app() 工厂函数，先通过 load_config + AppContainer 初始化配置和 DI 容器，再注册所有路由蓝图 + CORS + 日志 + OTel + 生命周期


层&依赖：bootstrap 层，依赖 interface/rest/routes
"""

from __future__ import annotations

from pathlib import Path

from quart import Quart
from quart_cors import cors

from flypig.bootstrap.container import AppContainer
from flypig.bootstrap.lifecycle import LifecycleEvents
from flypig.bootstrap.logging import init_logging
from flypig.bootstrap.otel import init_otel
from flypig.bootstrap.settings import load_config
from flypig.interface.rest.routes.chat_routes import chat_bp

# 蓝图注册所需的导入（移至文件顶部避免惰性 import）
from flypig.interface.rest.routes.config_routes import config_bp
from flypig.interface.rest.routes.files_routes import files_bp
from flypig.interface.rest.routes.graph_routes import graph_bp
from flypig.interface.rest.routes.health_routes import health_bp
from flypig.interface.rest.routes.pricing_routes import pricing_bp
from flypig.shared.settings import AppSettings


def _register_blueprints(app: Quart) -> None:
    """注册所有 REST 路由蓝图"""
    app.register_blueprint(config_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(pricing_bp)
    app.register_blueprint(graph_bp)


def _init_container(app: Quart, container: AppContainer, settings: AppSettings) -> None:
    """初始化 DI 容器并挂载到 app config"""
    workspace_dir = Path(settings.workspace) if settings.workspace else Path.cwd()

    # 将 AppSettings 转为 dict 注入 config（pydantic 对象不支持 .get()）
    config_dict = settings.model_dump()
    config_dict["workspace_dir"] = str(workspace_dir)
    config_dict["app_settings"] = settings  # 原始 AppSettings 对象，供 chat_service 等使用
    container.config.from_dict(config_dict)

    pricing_service = container.pricing_service()

    app.config["flypig_settings"] = settings
    app.config["flypig_container"] = container
    app.config["flypig_model_registry"] = container.model_registry()
    app.config["flypig_model_factory"] = container.model_factory()
    app.config["flypig_pricing_service"] = pricing_service
    app.config["flypig_chat_service"] = container.chat_service()
    app.config["flypig_tool_executor"] = container.tool_executor()


def _register_lifecycle(app: Quart, pricing_service) -> None:
    """注册应用生命周期事件"""
    events = LifecycleEvents()
    app.config["flypig_events"] = events

    # 注册 MCP 网关启动/关闭
    @events.on_startup
    async def _start_mcp_gateway() -> None:
        from flypig.infrastructure.tools.mcp.tool_mcp_loader import init_mcp_gateway

        await init_mcp_gateway()  # 服务器列表来自 model_registry.json → mcp.servers
        # MCP 工具注册完毕后，刷新 ToolExecutor 实例列表
        executor = app.config.get("flypig_tool_executor")
        if executor:
            executor.load_all()

    @events.on_shutdown
    async def _stop_mcp_gateway() -> None:
        from flypig.infrastructure.tools.mcp.tool_mcp_loader import get_mcp_gateway

        gw = get_mcp_gateway()
        if gw:
            await gw.shutdown_all()

    @app.before_serving
    async def startup() -> None:
        pricing_service.start()
        await events.fire_startup()

    @app.after_serving
    async def shutdown() -> None:
        pricing_service.stop()
        await events.fire_shutdown()


def create_app(
    config_path: str | Path | None = None,
    settings: AppSettings | None = None,
) -> Quart:
    """创建并配置 Quart 应用实例"""
    if settings is None:
        settings = load_config(config_path)

    init_logging(level=settings.log_level)
    init_otel()  # 全链路追踪（Jaeger 不可用时自动降级为 noop）

    container = AppContainer()

    app = Quart(__name__)

    _init_container(app, container, settings)
    app = cors(app, allow_origin="*")
    _register_blueprints(app)

    pricing_service = app.config["flypig_pricing_service"]
    _register_lifecycle(app, pricing_service)

    return app
