"""pricing

为什么做：前端需要显示各模型实时价格，需要从 Portkey API 抓取 + 本地缓存 + 每日自动刷新

实现方法：PricingService 封装了从 Portkey 抓取、USD→CNY 汇率转换、本地缓存（pricing_cache.json）、每日自动刷新循环

层&依赖：infrastructure.usage 层，依赖 domain.registry
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from flypig.domain.registry import ModelRegistry

# ── 常量 ──
DEFAULT_EXCHANGE_CACHE_TTL = 3600  # 汇率缓存 1 小时
EXCHANGE_RATE_TIMEOUT = 5  # 汇率 API 超时秒数
DEFAULT_REFRESH_INTERVAL = 86400  # 定价刷新间隔 24 小时


class PricingService:
    """定价服务 — 从 Portkey API 获取模型价格并缓存"""

    def __init__(
        self,
        registry: ModelRegistry,
        data_dir: Optional[Path] = None,
    ) -> None:
        self._registry = registry
        self._data_dir = data_dir or Path(__file__).resolve().parent.parent.parent / "data"
        self._cache_file = self._data_dir / "pricing_cache.json"
        self._exchange_rate: dict[str, float | None] = {"rate": None, "ts": 0.0}
        self._loop_task: Optional[asyncio.Task[None]] = None

    # ── 内部辅助 ──

    def _pricing_cfg(self, key: str, default=None):
        return self._registry.get_pricing_config().get(key, default)

    def _cache_path(self) -> Path:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        return self._cache_file

    def _load_cache(self) -> dict | None:
        path = self._cache_path()
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def _save_cache(self, data: dict) -> None:
        path = self._cache_path()
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass  # 缓存写入失败不影响主流程

    # ── 汇率 ──

    def _fetch_exchange_rate(self) -> float:
        now = datetime.now().timestamp()
        cache_ttl = self._pricing_cfg("exchange_rate_cache_ttl", DEFAULT_EXCHANGE_CACHE_TTL)
        rate_val = self._exchange_rate["rate"]
        ts_val = self._exchange_rate["ts"]
        if ts_val is not None and now - ts_val < cache_ttl and rate_val is not None:
            return rate_val  # type: ignore[return-value]

        api_url = self._pricing_cfg("exchange_rate_api")
        if not api_url:
            return float(self._pricing_cfg("fallback_usd_cny", 7.2))

        try:
            timeout = self._pricing_cfg("exchange_rate_timeout", EXCHANGE_RATE_TIMEOUT)
            resp = httpx.get(api_url, timeout=timeout)
            if resp.status_code == 200:
                rate = resp.json().get("rates", {}).get("CNY")
                if rate:
                    rate = round(float(rate), 4)
                    self._exchange_rate["rate"] = rate
                    self._exchange_rate["ts"] = now
                    return rate
        except Exception:
            pass

        return float(self._pricing_cfg("fallback_usd_cny", 7.2))

    def _convert_to_cny(self, prices: dict) -> dict:
        rate = self._fetch_exchange_rate()
        converted = {}
        for name, p in prices.items():
            cp = {}
            for key in ("input", "output", "input_cache_hit"):
                val = p.get(key)
                cp[key] = round(val * rate, 4) if val is not None else None
            converted[name] = cp
        return converted

    # ── Portkey 数据抓取 ──

    def _fetch_portkey_provider(self, provider: str) -> dict:
        pricing = self._registry.get_pricing_config()
        base = pricing.get("portkey_base")
        if not base:
            return {}
        timeout = pricing.get("timeout", 10)

        provider_lower = provider.lower()
        url = f"{base}/{provider_lower}.json"
        try:
            resp = httpx.get(url, timeout=timeout)
            if resp.status_code != 200:
                return {}
            return resp.json()
        except Exception:
            return {}

    def _extract_model_price(self, portkey_data: dict, model_name: str) -> Optional[dict]:
        """通过 ACL 将 Portkey 格式转为 dict（向后兼容）"""
        from flypig.acl.pricing import portkey_to_pricing_entry

        meta = self._registry.resolve(model_name)
        if not meta:
            return None
        api_model = meta.get("api_model")
        if not api_model:
            return None

        entry = portkey_to_pricing_entry(portkey_data, api_model)
        if entry is None:
            return None
        result: dict[str, float] = {}
        if entry.input_price is not None:
            result["input"] = entry.input_price
        if entry.output_price is not None:
            result["output"] = entry.output_price
        if entry.input_cache_hit is not None:
            result["input_cache_hit"] = entry.input_cache_hit
        return result if "input" in result and "output" in result else None

    def _load_defaults(self) -> dict:
        from flypig.acl.pricing import default_pricing_to_entry

        defaults = {}
        for name in self._registry.known_models():
            meta = self._registry.resolve(name)
            if meta:
                pricing = meta.get("default_pricing")
                if pricing is not None:
                    entry = default_pricing_to_entry(pricing)
                    d: dict[str, float] = {}
                    if entry.input_price is not None:
                        d["input"] = entry.input_price
                    if entry.output_price is not None:
                        d["output"] = entry.output_price
                    if entry.input_cache_hit is not None:
                        d["input_cache_hit"] = entry.input_cache_hit
                    defaults[name] = d
        return defaults

    def _scrape_pricing(self) -> dict:
        prices = {}

        provider_models: dict[str, list[str]] = {}
        for name, meta in self._registry.all_models.items():
            provider = meta.get("provider", "")
            provider_models.setdefault(provider, []).append(name)

        for provider, model_names in provider_models.items():
            portkey_data = self._fetch_portkey_provider(provider)
            if not portkey_data:
                continue
            for model_name in model_names:
                price = self._extract_model_price(portkey_data, model_name)
                if price:
                    prices[model_name] = price

        for name, price in self._load_defaults().items():
            prices[name] = price

        return prices

    # ── 公开 API ──

    def fetch_pricing(self, currency: str = "USD") -> dict:
        """获取价格数据，缓存优先"""
        today = str(date.today())
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        cache = self._load_cache()
        if cache and cache.get("updated") == today:
            prices = dict(cache.get("prices", {}))
            cached_update_time = cache.get("update_time", today)
        else:
            prices = self._scrape_pricing()

            if cache:
                for name, price in cache.get("prices", {}).items():
                    if name not in prices:
                        prices[name] = price

            self._save_cache({
                "prices": prices,
                "updated": today,
                "update_time": now_iso,
            })
            cached_update_time = now_iso

        if currency.upper() == "CNY":
            prices = self._convert_to_cny(prices)
            rate = self._fetch_exchange_rate()
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

    def get_pricing(self, model_name: str) -> Optional[dict]:
        """获取单个模型价格"""
        cache = self._load_cache()
        if cache:
            return cache.get("prices", {}).get(model_name)
        return None

    def start(self) -> None:
        """启动后台定价刷新循环（每天早上 0 点自动刷新）"""
        async def _loop():
            refresh_interval = self._pricing_cfg("refresh_interval", DEFAULT_REFRESH_INTERVAL)
            try:
                self.fetch_pricing()
                logger.info("[pricing] 预热完成，每天自动刷新")
            except Exception as e:
                logger.warning("[pricing] 预热失败: {}，使用默认价格", e)
            while True:
                await asyncio.sleep(refresh_interval)
                try:
                    self.fetch_pricing()
                except Exception:
                    pass

        self._loop_task = asyncio.create_task(_loop())

    def stop(self) -> None:
        """停止后台循环"""
        if self._loop_task is not None:
            self._loop_task.cancel()
            self._loop_task = None
