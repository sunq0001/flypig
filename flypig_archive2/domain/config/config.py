"""Config — 读取/写入 config.yaml，提供全局配置

为什么做：所有运行时配置（工作区、模型、API Key、模式等）集中管理，
后端各模块和前端 /api/config 端点从同一来源读取，消除"前端硬编码默认值"问题。

实现方法：Config 类在启动时加载 config.yaml 到内存，
提供 get/save 方法，修改时同步写回 yaml 文件。

实现效果：
- 前端 GET /api/config 拿到所有配置，不做任何默认值假设
- 修改配置（工作区、API Key 等）通过 POST 端点写入 yaml
- 重启后配置从 yaml 恢复

技术栈：PyYAML, pathlib

注意事项：
- /api/config 是前端配置的唯一来源，前端不做任何默认值假设
- 返回的配置包含 workspace / default_model / models / mode / theme 等全部运行时状态
- 前端初始状态：config / workspace / model / mode 全为 null，GET /api/config 后才赋值
- default_model 来自 config.yaml 的 llm.default_model 字段，非硬编码
- 修改配置（工作区、API Key 等）通过 POST 端点写入 yaml，重启后从 yaml 恢复
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from domain.config.model_registry import REGISTRY


class Config:
    def __init__(self, config_path: str | Path | None = None):
        if config_path is None:
            # domain/config/config.py → domain/config/ → domain/ → flypig/
            config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
        self._config_path = Path(config_path)
        self._ensure_config()
        self.reload()

    # ── 读取 ──────────────────────────────────────────────

    def reload(self):
        with open(self._config_path, encoding="utf-8") as f:
            self._data: dict = yaml.safe_load(f) or {}

    @property
    def workspace(self) -> str | None:
        w = self._data.get("agent", {}).get("workspace")
        return w if w and w != "~" else None

    @property
    def recent_workspaces(self) -> list[str]:
        """最近使用的工作区列表（最多 10 个，最新在前）"""
        return self._data.get("agent", {}).get("recent_workspaces", [])

    @property
    def default_model_name(self) -> str:
        return self._data.get("llm", {}).get("default_model", "deepseek-v4-flash")

    @property
    def mode(self) -> str:
        return self._data.get("agent", {}).get("mode", "explore")

    @property
    def models(self) -> list[dict]:
        """返回所有模型列表（注册表 + 本地动态发现），附带 has_key 状态"""
        api_keys = self._data.get("api_keys", {})
        result = []
        for name, meta in REGISTRY.items():
            provider = meta["provider"]
            has_key = bool(api_keys.get(provider))
            result.append(
                {
                    "name": name,
                    "provider": provider,
                    "base_url": meta.get("base_url", ""),
                    "api_model": meta.get("model", ""),
                    "local": False,
                    "has_key": has_key,
                }
            )
        # 追加 Ollama 本地模型（动态查询 /api/tags）
        from domain.config.model_registry import get_local_models

        result.extend(get_local_models())
        return result

    def api_configured(self) -> bool:
        """至少一个提供商配置了 Key"""
        return any(k for k in self._data.get("api_keys", {}).values())

    def get_api_key(self, provider: str) -> str | None:
        api_keys = self._data.get("api_keys", {})
        key = api_keys.get(provider)
        if not key:
            return None
        # 支持 ${ENV_VAR} 环境变量引用
        if key.startswith("${") and key.endswith("}"):
            env_name = key[2:-1]
            return os.environ.get(env_name)
        return key

    # ── 写入 ──────────────────────────────────────────────

    def _ensure_config(self):
        if not self._config_path.exists():
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            default = {
                "agent": {"workspace": "~"},
                "llm": {"default_model": "deepseek-v4-flash"},
                "api_keys": {},
            }
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(default, f, default_flow_style=False, allow_unicode=True)

    def set_workspace(self, path: str):
        self._ensure_agent_section()
        self._data["agent"]["workspace"] = path
        # 更新最近使用列表（去重 + 置顶 + 上限 10）
        recent: list = self._data["agent"].get("recent_workspaces", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._data["agent"]["recent_workspaces"] = recent[:10]
        self._flush()

    def set_default_model(self, model_name: str):
        if "llm" not in self._data:
            self._data["llm"] = {}
        self._data["llm"]["default_model"] = model_name
        self._flush()

    def save_api_key(self, provider: str, api_key: str):
        if "api_keys" not in self._data:
            self._data["api_keys"] = {}
        self._data["api_keys"][provider] = api_key
        self._flush()

    def _ensure_agent_section(self):
        if "agent" not in self._data:
            self._data["agent"] = {}

    def _flush(self):
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    # ── 序列化（给前端） ──────────────────────────────────

    def to_frontend(self) -> dict:
        return {
            "workspace": self.workspace,
            "default_model": self.default_model_name,
            "models": self.models,
            "mode": self.mode,
            "api_configured": self.api_configured(),
            "recent_workspaces": self.recent_workspaces,
            "version": "0.1.0",
        }
