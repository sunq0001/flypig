"""定价路由 (/api/pricing)

为什么做：前端模型下拉 hover 时需要显示各模型价格，从缓存获取，毫秒级返回。

实现方法：Quart GET 端点，调用 pricing.fetch_pricing() 返回 {prices, updated, source}。

实现效果：前端 tooltip 展示价格 + 更新时间。

技术栈：Quart Blueprint

层&依赖：backend.routes 层，依赖 infrastructure.usage.pricing
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""

from quart import Blueprint, current_app

from infrastructure.usage.pricing import fetch_pricing

pricing_bp = Blueprint("pricing", __name__)


@pricing_bp.route("/api/pricing")
async def pricing():
    return fetch_pricing()


@pricing_bp.route("/api/routes")
async def list_routes():
    rules = sorted([r.rule for r in current_app.url_map.iter_rules()])
    return {"routes": rules}
