"""pricing_routes

为什么做：前端需要获取模型价格信息

实现方法：GET /api/pricing 返回 PricingService.fetch_pricing() 结果

层&依赖：interface.rest.routes 层
"""

import asyncio

from quart import Blueprint, current_app, jsonify, request

from flypig.infrastructure.usage.pricing import PricingService

pricing_bp = Blueprint("pricing", __name__)
_refreshing = False


def _get_pricing_service() -> PricingService:
    return current_app.config["flypig_pricing_service"]


@pricing_bp.route("/api/pricing")
async def pricing():
    """返回价格数据，缓存优先，后台异步刷新

    查询参数:
        currency: "USD"（默认）| "CNY" — 按实时汇率转换
    """
    global _refreshing

    currency = request.args.get("currency", "USD")
    service = _get_pricing_service()
    result = service.fetch_pricing(currency=currency)

    # 如果没有今日缓存，后台异步刷新（不阻塞请求）
    if result.get("source") != "cached" and not _refreshing:
        _refreshing = True
        asyncio.ensure_future(_refresh_background())

    return jsonify(result)


@pricing_bp.route("/api/routes")
async def list_routes():
    rules = sorted([r.rule for r in current_app.url_map.iter_rules()])
    return jsonify({"routes": rules})


async def _refresh_background():
    """后台刷新定价缓存"""
    global _refreshing
    try:
        await asyncio.sleep(2)  # 延迟 2 秒，不阻塞启动
        service = _get_pricing_service()
        service.fetch_pricing()
    finally:
        _refreshing = False
