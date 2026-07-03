"""Pricing — 模型价格获取（从 Portkey 定价 API 获取 + 本地缓存）

配置数据全部来自 model_registry.json 的 pricing 段：
portkey_base、exchange_rate_api、timeout、fallback_usd_cny 等。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from flypig.domain.model_ref import REGISTRY, get_pricing_config, get_portkey_provider

# --- 缓存 ---
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_CACHE_FILE = _CACHE_DIR / "pricing_cache.json"
_MODEL_REGISTRY_FILE = _CACHE_DIR / "model_registry.json"

_EXCHANGE_RATE_CACHE = {"rate": None, "ts": 0}


def _pricing_cfg(key: str, default=None):
    return get_pricing_config().get(key, default)


def _fetch_exchange_rate() -> float:
    now = datetime.now().timestamp()
    cache_ttl = _pricing_cfg("exchange_rate_cache_ttl", 3600)
    if now - _EXCHANGE_RATE_CACHE["ts"] < cache_ttl and _EXCHANGE_RATE_CACHE["rate"] is not None:
        return _EXCHANGE_RATE_CACHE["rate"]

    api_url = _pricing_cfg("exchange_rate_api")
    if not api_url:
        return _pricing_cfg("fallback_usd_cny", 7.2)

    try:
        timeout = _pricing_cfg("exchange_rate_timeout", 5)
        resp = httpx.get(api_url, timeout=timeout)
        if resp.status_code == 200:
            rate = resp.json().get("rates", {}).get("CNY")
            if rate:
                rate = round(float(rate), 4)
                _EXCHANGE_RATE_CACHE["rate"] = rate
                _EXCHANGE_RATE_CACHE["ts"] = now
                return rate
    except Exception:
        pass

    return _pricing_cfg("fallback_usd_cny", 7.2)


def _convert_to_cny(prices: dict) -> dict:
    rate = _fetch_exchange_rate()
    converted = {}
    for name, p in prices.items():
        cp = {}
        for key in ("input", "output", "input_cache_hit"):
            val = p.get(key)
            cp[key] = round(val * rate, 4) if val is not None else None
        converted[name] = cp
    return converted


def _load_model_registry() -> dict:
    try:
        if _MODEL_REGISTRY_FILE.exists():
            with open(_MODEL_REGISTRY_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _load_defaults() -> dict:
    registry = _load_model_registry()
    defaults = {}
    for name, m in registry.get("models", {}).items():
        pricing = m.get("default_pricing")
        if pricing is not None:
            defaults[name] = pricing
    return defaults


def _resolve_portkey_name(provider: str) -> str:
    """根据 provider 解析 Portkey API 文件名

    规则：默认 provider.lower()，有 portkey_provider 字段的走覆盖
    实际覆盖在 get_portkey_provider(model_name) 中处理，此处仅做 fallback
    """
    return provider.lower()


def _portkey_price_to_usd_per_1m(cents_per_token: float | None) -> float | None:
    if cents_per_token is None:
        return None
    return round(cents_per_token * 10000, 4)


def _fetch_portkey_provider(provider: str) -> dict:
    from flypig.domain.model_ref import get_pricing_config

    pricing = get_pricing_config()
    base = pricing.get("portkey_base")
    if not base:
        return {}
    timeout = pricing.get("timeout", 10)

    portkey_name = _resolve_portkey_name(provider)
    url = f"{base}/{portkey_name}.json"
    try:
        resp = httpx.get(url, timeout=timeout)
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


def _extract_model_price(portkey_data: dict, model_name: str) -> Optional[dict]:
    meta = REGISTRY.get(model_name, {})
    api_model = meta.get("api_model")
    if not api_model:
        return None

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
    prices = {}

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

    for name, price in _load_defaults().items():
        prices[name] = price

    return prices


def fetch_pricing(currency: str = "USD") -> dict:
    today = str(date.today())
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cache = _load_cache()
    if cache and cache.get("updated") == today:
        prices = dict(cache.get("prices", {}))
        cached_update_time = cache.get("update_time", today)
    else:
        prices = _scrape_pricing()

        if cache:
            for name, price in cache.get("prices", {}).items():
                if name not in prices:
                    prices[name] = price

        _save_cache({
            "prices": prices,
            "updated": today,
            "update_time": now_iso,
        })
        cached_update_time = now_iso

    if currency.upper() == "CNY":
        prices = _convert_to_cny(prices)
        rate = _fetch_exchange_rate()
    else:
        rate = None

    return {
        "prices": prices,
        "updated": today,
        "update_time": cached_update_time,
        "currency": currency.upper(),
        "exchange_rate": rate,
        "source": "cached" if cache and cache.get("updated") == today else "online",
    }


def get_pricing(model_name: str) -> Optional[dict]:
    cache = _load_cache()
    if cache:
        return cache.get("prices", {}).get(model_name)
    return None


def start_pricing_loop():
    import asyncio
    from loguru import logger
    from flypig.domain.model_ref import get_pricing_config

    async def _loop():
        refresh_interval = get_pricing_config().get("refresh_interval", 86400)
        try:
            fetch_pricing()
            logger.info("[pricing] 预热完成，每天自动刷新")
        except Exception as e:
            logger.warning("[pricing] 预热失败: {}，使用默认价格", e)
        while True:
            await asyncio.sleep(refresh_interval)
            try:
                fetch_pricing()
            except Exception:
                pass
    asyncio.create_task(_loop())
