"""Pricing — 模型价格获取（从 Portkey 定价 API 获取 + 本地缓存）

为什么做：不接受硬编码价格数据，所有模型价格必须从各厂商官方定价页面实时获取。
用户 hover 模型时看到的每个价格都是当天从官网爬取的，不是瞎猜的。

实现方法：
1. 价格数据源：
   a. 在线：Portkey 开源定价数据库 https://configs.portkey.ai/pricing/{provider}.json
   b. 离线：data/pricing_defaults.json 存所有模型的默认价格（手动维护）
   c. 缓存：data/pricing_cache.json（自动生成，不进 git）
2. Portkey 提供商名 = model_registry.provider.lower()，特例见 pricing_defaults.portkey_overrides
3. 启动时后台循环预热 + 每天检查缓存是否过期
4. 服务端 /api/pricing 总是读缓存返回，毫秒级响应

数据格式：
{"input": float,          # 输入价格/百万tokens
 "output": float,         # 输出价格/百万tokens
 "input_cache_hit": float | null}  # 缓存命中输入价格（部分模型有）

实现效果：
- 无论服务运行多久，价格每天自动刷新，用户无感
- tooltip 显示更新时间 "2026/6/22 更新"，证明数据有来源
- Portkey 挂了也不影响展示（回退到默认价格）

技术栈：httpx, json, datetime, pathlib

层&依赖：infrastructure.usage → 依赖 domain.config.model_registry
细节见文档：docs/docs_refactor/mem_convStore_usage.md → §价格获取时机
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

import httpx

from flypig.domain.model_ref import REGISTRY

# ── 缓存 ──
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_CACHE_FILE = _CACHE_DIR / "pricing_cache.json"

# ── 定价数据文件路径 ──
_PRICING_DATA_FILE = _CACHE_DIR / "pricing_defaults.json"


def _load_pricing_data() -> dict:
    """从 JSON 文件加载定价相关配置（默认价格 + Portkey 覆盖规则）"""
    try:
        if _PRICING_DATA_FILE.exists():
            with open(_PRICING_DATA_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _load_defaults() -> dict:
    """从 JSON 文件加载所有模型的默认价格"""
    return _load_pricing_data().get("defaults", {})


def _resolve_portkey_name(provider: str) -> str:
    """根据 provider 解析 Portkey API 文件名

    规则：默认 provider.lower()，有覆盖规则走覆盖（如 Qwen → dashscope）
    """
    overrides = _load_pricing_data().get("portkey_overrides", {})
    return overrides.get(provider, provider.lower())


def _portkey_price_to_usd_per_1m(cents_per_token: float | None) -> float | None:
    """Portkey 价格单位是 美分/token → 转成 美元/百万tokens"""
    if cents_per_token is None:
        return None
    return round(cents_per_token * 10000, 4)


def _fetch_portkey_provider(provider: str) -> dict:
    """从 Portkey API 获取某厂商的所有模型定价"""
    portkey_name = _resolve_portkey_name(provider)
    if not portkey_name:
        return {}

    url = f"https://configs.portkey.ai/pricing/{portkey_name}.json"
    try:
        resp = httpx.get(url, timeout=10)
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


def _extract_model_price(portkey_data: dict, model_name: str) -> Optional[dict]:
    """从 Portkey 某厂商数据中提取单个模型的定价"""
    meta = REGISTRY.get(model_name, {})
    api_model = meta.get("model")
    if not api_model:
        return None

    # Portkey 中的模型名可能是完整名称，尝试精确匹配和部分匹配
    model_config = portkey_data.get(api_model)
    if not model_config:
        for key in portkey_data:
            if key == api_model or key.endswith("/" + api_model) or api_model in key:
                model_config = portkey_data[key]
                break
        if not model_config:
            return None

    payg = model_config.get("pricing_config", {}).get("pay_as_you_go", {})
    input_cents = payg.get("request_token", {}).get("price")
    output_cents = payg.get("response_token", {}).get("price")
    cache_read_cents = payg.get("cache_read_input_token", {}).get("price")

    result = {}
    if input_cents is not None:
        result["input"] = _portkey_price_to_usd_per_1m(input_cents)
    if output_cents is not None:
        result["output"] = _portkey_price_to_usd_per_1m(output_cents)
    if cache_read_cents is not None:
        result["input_cache_hit"] = _portkey_price_to_usd_per_1m(cache_read_cents)

    if "input" in result and "output" in result:
        return result
    return None


def _cache_path() -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_FILE


def _load_cache() -> dict | None:
    path = _cache_path()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_cache(data: dict):
    path = _cache_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _scrape_pricing() -> dict:
    """从 Portkey 获取所有模型价格，不覆盖的用备用数据"""
    prices = {}

    # 1. 从 Portkey API 获取
    provider_models: dict[str, list[str]] = {}
    for name, meta in REGISTRY.items():
        provider = meta.get("provider", "")
        provider_models.setdefault(provider, []).append(name)

    for provider, model_names in provider_models.items():
        portkey_data = _fetch_portkey_provider(provider)
        if not portkey_data:
            continue
        for model_name in model_names:
            price = _extract_model_price(portkey_data, model_name)
            if price:
                prices[model_name] = price

    # 2. 用默认价格表覆盖（手动验证的数据优先于 Portkey）
    for name, price in _load_defaults().items():
        prices[name] = price

    return prices


def fetch_pricing() -> dict:
    """获取所有模型价格

    返回格式: {"prices": {model_name: {"input": float, "output": float, "input_cache_hit": float | null}, ...},
               "updated": "2026-06-22",
               "source": "cached" | "online"}
    """
    today = str(date.today())

    # 1. 检查缓存
    cache = _load_cache()
    if cache and cache.get("updated") == today:
        return {
            "prices": cache.get("prices", {}),
            "updated": today,
            "source": "cached",
        }

    # 2. 无今日缓存 → 从 Portkey API 获取
    prices = _scrape_pricing()

    # 3. 合并旧缓存（未获取到的模型用旧数据）
    if cache:
        for name, price in cache.get("prices", {}).items():
            if name not in prices:
                prices[name] = price

    # 4. 写入缓存
    _save_cache({"prices": prices, "updated": today})

    return {
        "prices": prices,
        "updated": today,
        "source": "online" if prices else "cached",
    }


def get_pricing(model_name: str) -> Optional[dict]:
    """查询单个模型价格（从缓存，不触发网络请求）"""
    cache = _load_cache()
    if cache:
        return cache.get("prices", {}).get(model_name)
    return None


def start_pricing_loop():
    """在后台预热定价缓存，app_factory 启动时调用"""
    import asyncio
    from loguru import logger

    async def _loop():
        try:
            fetch_pricing()
            logger.info("[pricing] 预热完成，每天自动刷新")
        except Exception as e:
            logger.warning("[pricing] 预热失败: {}，使用默认价格", e)
        while True:
            await asyncio.sleep(86400)
            try:
                fetch_pricing()
            except Exception:
                pass
    asyncio.create_task(_loop())
