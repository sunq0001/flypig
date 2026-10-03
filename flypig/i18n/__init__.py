"""i18n — 异常 code 到用户文案的映射

为什么做：FlyPigException 携带 code 字段（前端据此匹配文案），但项目里一直没有
         翻译表，异常只能把技术信息直接抛给用户。
实现方法：读取同目录 translations.yaml（code → 中文文案），对外暴露
         translate(code, default) 供接口层/前端使用。
层&依赖：i18n 包，依赖 yaml 与 domain 层定义的异常 code
"""

from __future__ import annotations

from pathlib import Path

import yaml

__all__ = ["load_translations", "translate"]

_TRANSLATIONS_FILE = Path(__file__).resolve().parent / "translations.yaml"


def load_translations() -> dict[str, str]:
    """读取 translations.yaml（文件缺失或解析失败时返回空表）"""
    if not _TRANSLATIONS_FILE.exists():
        return {}
    try:
        data = yaml.safe_load(_TRANSLATIONS_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def translate(code: str, default: str = "") -> str:
    """把异常 code 翻译为文案；未收录时返回 default（无 default 则返回 code 本身）"""
    return load_translations().get(code) or default or code
