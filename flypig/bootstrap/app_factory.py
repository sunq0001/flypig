"""app_factory

为什么做：后端的 Web 入口需要统一创建 app 实例、注册蓝图、配置中间件

实现方法：create_app() 工厂函数，先通过 load_config + AppContainer 初始化配置和 DI 容器，
         再注册所有路由蓝图 + CORS + 日志 + OTel + 生命周期

层&依赖：bootstrap 层（胶水代码），依赖 interface/rest/routes + infrastructure
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from quart import Quart
from quart_cors import cors

from flypig.bootstrap.container import AppContainer
from flypig.bootstrap.lifecycle import LifecycleEvents
from flypig.bootstrap.logging import init_logging
from flypig.bootstrap.otel import init_otel
from flypig.bootstrap.settings import load_config
from flypig.infrastructure.files.file_watcher import FileWatcherService
from flypig.infrastructure.tools.mcp.tool_mcp_loader import get_mcp_gateway, init_mcp_gateway
from flypig.interface.rest.routes.chat_routes import chat_bp
from flypig.interface.rest.routes.config_routes import config_bp
from flypig.interface.rest.routes.file_events_routes import file_events_bp
from flypig.interface.rest.routes.files_routes import files_bp
from flypig.interface.rest.routes.graph_routes import graph_bp
from flypig.interface.rest.routes.health_routes import health_bp
from flypig.interface.rest.routes.pricing_routes import pricing_bp
from flypig.interface.rest.routes.tool_events_routes import tool_events_bp
from flypig.shared.settings import AppSettings

_log = logging.getLogger(__name__)


def _register_blueprints(app: Quart) -> None:
    """注册所有 REST 路由蓝图（2026-07-27 新增 tool_events/file_events）"""
    app.register_blueprint(config_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(pricing_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(file_events_bp)
    app.register_blueprint(tool_events_bp)


def _init_container(app: Quart, container: AppContainer, settings: AppSettings) -> None:
    """初始化 DI 容器并挂载到 app config"""
    workspace_dir = Path(settings.workspace) if settings.workspace else None

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


def _register_mcp_events(events: LifecycleEvents, app: Quart) -> None:
    """注册 MCP 网关的启动/关闭事件"""

    @events.on_startup
    async def _start_mcp_gateway() -> None:
        try:
            await init_mcp_gateway()  # 服务器列表来自 model_registry.json → mcp.servers
            # MCP 工具注册完毕后，刷新 ToolExecutor 实例列表
            executor = app.config.get("flypig_tool_executor")
            if executor:
                executor.load_all()
        except Exception as e:
            # MCP 是增强能力，启动失败不应阻断应用
            _log.warning("MCP 网关启动失败: %s", e)

    @events.on_shutdown
    async def _stop_mcp_gateway() -> None:
        try:
            gw = get_mcp_gateway()
            if gw:
                await gw.shutdown_all()
        except Exception as e:
            _log.warning("MCP 网关关闭异常: %s", e)


def _register_serving_events(app: Quart, events: LifecycleEvents, pricing_service) -> None:
    """注册 before_serving / after_serving 事件（定价刷新 + 文件监听）"""

    @app.before_serving
    async def startup() -> None:
        try:
            pricing_service.start()

            # ── 启动文件监听（watchdog，AI 改文件后推 SSE 通知前端） ──
            settings = app.config.get("flypig_settings")
            if settings and settings.workspace:
                watcher = FileWatcherService(settings.workspace)
                watcher.start()
                app.config["flypig_file_watcher"] = watcher
                _log.info("文件监听已注册")

            await events.fire_startup()
        except Exception as e:
            _log.error("应用启动流程异常: %s", e)
            raise

    @app.after_serving
    async def shutdown() -> None:
        try:
            pricing_service.stop()

            # ── 停止文件监听 ──
            watcher = app.config.get("flypig_file_watcher")
            if watcher:
                watcher.stop()

            await events.fire_shutdown()
        except Exception as e:
            _log.warning("应用关闭流程异常: %s", e)


def _register_lifecycle(app: Quart, pricing_service) -> None:
    """注册应用生命周期事件"""
    events = LifecycleEvents()
    app.config["flypig_events"] = events
    _register_mcp_events(events, app)
    _register_serving_events(app, events, pricing_service)


def _load_recent_workspace() -> str | None:
    """从 recent_workspaces.json 读取最近使用的工作区"""
    recent_file = (
        Path(__file__).resolve().parent.parent
        / "interface"
        / "flypig"
        / "data"
        / "recent_workspaces.json"
    )
    if not recent_file.exists():
        return None

    recent: str | None = None
    try:
        data = json.loads(recent_file.read_text(encoding="utf-8"))
        if data and isinstance(data, list) and len(data) > 0:
            recent = data[0]
    except Exception as e:
        _log.debug("读取最近工作区失败: %s", e)
    return recent


def create_app(
    config_path: str | Path | None = None,
    settings: AppSettings | None = None,
) -> Quart:
    """创建并配置 Quart 应用实例"""
    if settings is None:
        settings = load_config(config_path)

    # 启动时自动恢复最近使用的工作区
    if not settings.workspace:
        recent = _load_recent_workspace()
        if recent:
            settings.workspace = recent

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
