"""健康检查路由 (/api/health /api/ping)

层&amp;依赖：interface.rest.routes 层，零依赖
"""

from quart import Blueprint

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@health_bp.route("/api/ping")
async def ping():
    return {"pong": True}
