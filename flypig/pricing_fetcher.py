"""模型价格自动获取与内置参考表"""
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

# ============================================================
# 内置价格参考表（$/1M tokens）— 出厂默认值，仅当无缓存且在线失败时用
# ============================================================
BUILTIN_PRICES = {
    # ── DeepSeek ──
    "deepseek-chat":       {"input": 0.14,   "output": 0.28},
    "deepseek-v4-flash":   {"input": 0.14,   "output": 0.28},
    "deepseek-v4-pro":     {"input": 0.435,  "output": 0.87},
    "deepseek-reasoner":   {"input": 0.14,   "output": 0.28},

    # ── OpenAI ──
    "gpt-4o-mini":         {"input": 0.15,   "output": 0.60},
    "gpt-4o":              {"input": 2.50,   "output": 10.00},

    # ── Anthropic ──
    "claude-3-5-haiku":    {"input": 0.80,   "output": 4.00},
    "claude-3-5-sonnet":   {"input": 3.00,   "output": 15.00},
    "claude-4-opus":       {"input": 15.00,  "output": 75.00},
}

# 缓存文件路径（与内置表同目录）
_CACHE_PATH = Path(__file__).parent / "pricing_cache.json"


def _load_cache() -> dict:
    """加载本地价格缓存（缓存表 + 内置表，缓存优先）"""
    cache = dict(BUILTIN_PRICES)
    if _CACHE_PATH.exists():
        try:
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cache.update(cached)  # 缓存覆盖内置表
        except Exception:
            pass
    return cache


def _save_to_cache(model_name: str, prices: dict):
    """将在线获取的价格持久化到缓存文件"""
    try:
        data = {}
        if _CACHE_PATH.exists():
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[model_name] = prices
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# 官方价格页面 URL
PRICING_URLS = {
    "DeepSeek":  "https://api-docs.deepseek.com/quick_start/pricing",
    "OpenAI":    "https://openai.com/api/pricing/",
    "Anthropic": "https://www.anthropic.com/pricing",
}


def fetch_pricing(model_name: str, provider: str = "") -> Tuple[Optional[dict], Optional[str]]:
    """获取模型价格

    Returns:
        ({"input": float, "output": float}, source) — 成功
        (None, None) — 完全获取失败

    source 取值:
        "online"   — 从提供商官方页面抓取（会写入本地缓存）
        "cached"   — 本地价格缓存
        "builtin"  — 使用内置价格参考表
    """
    # 1. 优先在线抓取（最新价格）
    prices = _try_web_fetch(model_name, provider)
    if prices:
        _save_to_cache(model_name, prices)
        return prices, "online"

    # 2. 本地缓存（包含历史在线抓取结果）
    cache = _load_cache()
    if model_name in cache:
        return dict(cache[model_name]), "cached"

    # 3. 内置出厂表
    if model_name in BUILTIN_PRICES:
        return dict(BUILTIN_PRICES[model_name]), "builtin"

    return None, None


def _try_web_fetch(model_name: str, provider: str) -> Optional[dict]:
    """尝试从官方价格页抓取"""
    url = PRICING_URLS.get(provider)
    if not url:
        return None

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FlyPig/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        lines = html.split("\n")
        for i, line in enumerate(lines):
            if model_name.lower() in line.lower():
                context = "\n".join(lines[max(0, i - 2):i + 3])
                prices = _extract_prices(context)
                if prices:
                    return prices

    except Exception:
        pass

    return None


def _extract_prices(text: str) -> Optional[dict]:
    """从文本中提取 $X.XX 模式的价格"""
    amounts = [float(x) for x in re.findall(r'\$(\d+\.?\d*)', text)]
    amounts = [a for a in amounts if 0.001 < a < 500]

    if len(amounts) >= 2:
        return {"input": amounts[0], "output": amounts[1]}
    return None
