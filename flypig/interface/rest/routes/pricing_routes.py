"""定价路由 (/api/pricing)

层&amp;依赖：interface.rest.routes 层，依赖 infrastructure.usage.pricing
"""

import asyncio
from quart import Blueprint, current_app, jsonify

from flypig.infrastructure.usage.pricing import fetch_pricing

pricing_bp = Blueprint("pricing", __name__)
_refreshing = False


@pricing_bp.route("/api/pricing")
async def pricing():
    """返回价格数据，缓存优先，后台异步刷新"""
    global _refreshing
    
    result = fetch_pricing()
    
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
        fetch_pricing()
    finally:
        _refreshing = False
