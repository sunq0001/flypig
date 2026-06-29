"""健康检查路由 (/api/health /api/ping)

为什么做：Docker 容器和反向代理需要心跳检查，确认后端服务正常运行。

实现方法：Quart GET 端点，返回 {status: "ok"} / {"pong": true}。

实现效果：运维监控和 Docker 健康检查使用此端点，故障时自动重启。

技术栈：Quart Blueprint

层&依赖：backend.routes 层，零依赖
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""

from quart import Blueprint

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@health_bp.route("/api/ping")
async def ping():
    return {"pong": True}
