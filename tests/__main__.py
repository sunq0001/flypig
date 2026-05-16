"""测试入口 — 核心功能测试

用法:
  python -m tests                              # 全部
  python -m tests --func                        # 仅功能测试
  python -m tests --list                        # 列出所有 feature 模块

Features:
  integration   集成测试 (10)
"""

import argparse
import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

_FEATURES = {
    "integration":  "tests.test_integration",
}

_CATEGORY_LABEL = {"func": "功能测试"}


def _load_registries(feature_names=None):
    """加载指定 feature 的 REGISTRY；None=全部"""
    registry = []
    targets = feature_names if feature_names else list(_FEATURES)
    for name in targets:
        module_name = _FEATURES.get(name)
        if not module_name:
            continue
        import importlib
        mod = importlib.import_module(module_name)
        if hasattr(mod, "REGISTRY"):
            registry.extend(mod.REGISTRY)
    return registry
