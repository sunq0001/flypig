"""Quart 应用入口 + 路由注册

为什么做：所有 API 端点需要注册到 Quart 实例，并配置 CORS。

实现方法：create_app() 工厂函数，接收 Config 实例 → 注册蓝图 → CORS → 返回 app。

实现效果：启动时传入 Config，各路由通过 app.config 访问同一配置实例。

技术栈：Quart, Blueprint, CORS

热加载验证：改此文件后 uvicorn --reload 会自动重启服务器
"""

from pathlib import Path

from quart import Quart
from quart_cors import cors

from domain.config.config import Config


def create_app(config: Config | None = None) -> Quart:
    app = Quart(__name__)

    if config is None:
        config = Config()

    app.config["flypig_config"] = config

    # CORS（Vite proxy 在开发时处理跨域，生产用 nginx）
    app = cors(app, allow_origin="*")

    # 注册蓝图
    from backend.routes.config import config_bp
    from backend.routes.files import files_bp

    app.register_blueprint(config_bp)
    app.register_blueprint(files_bp)

    @app.route("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.route("/api/ping")
    async def ping():
        return {"pong": True}

    return app
