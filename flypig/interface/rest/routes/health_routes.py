"""health_routes

为什么做：健康检查端点，用于监控和负载均衡

实现方法：GET /api/health 返回 {'status': 'ok'}

层&依赖：interface.rest.routes 层
"""

from quart import Blueprint

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@health_bp.route("/api/ping")
async def ping():
    return {"pong": True}
