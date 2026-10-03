"""data 资源路径解析

为什么做：各层代码需要引用 data/ 下的 JSON 配置文件（model_registry.json 等），
         如果每个文件都自己算 Path(__file__).parent.parent... 会很脆弱且难看。
实现方法：get_data_path() 返回 data/ 目录路径，供各层统一调用。
层&依赖：shared 层（数据层），零外部依赖
"""

from __future__ import annotations

from pathlib import Path


def get_data_path() -> Path:
    """获取 data/ 目录的绝对路径

    通过 __file__ 定位（文件位于 flypig/data/__init__.py），
    比各模块自己写 Path(__file__).parent.parent... 更稳定。
    """
    return Path(__file__).resolve().parent


def get_registry_path() -> Path:
    """获取 model_registry.json 的绝对路径"""
    return get_data_path() / "model_registry.json"


def get_contracts_path() -> Path:
    """获取 api-contracts.json 的绝对路径"""
    return get_data_path() / "api-contracts.json"


__all__ = [
    "get_contracts_path",
    "get_data_path",
    "get_registry_path",
]
