"""配置加载"""
import os
import yaml
from pathlib import Path
from typing import List, Optional

from .model_registry import resolve as resolve_model_meta


class Config:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        self._config_path = Path(config_path)

        with open(self._config_path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

        self._resolve_env_vars()

    def _resolve_env_vars(self):
        """解析环境变量 ${VAR_NAME}"""
        def resolve(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.environ.get(env_var, "")
            elif isinstance(value, dict):
                return {k: resolve(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve(item) for item in value]
            return value

        self.data = resolve(self.data)

    # ── 模型列表 ──

    @property
    def models(self) -> List[dict]:
        """返回所有已注册模型的完整配置（从 model_registry 读取，同步 config 中的 Key）"""
        from .model_registry import REGISTRY
        result = []
        for name, meta in REGISTRY.items():
            result.append({
                "name": name,
                "provider": meta["provider"],
                "base_url": meta["base_url"],
                "api_key": self._get_provider_key(meta["provider"]),
            })
        return result

    @property
    def default_model_name(self) -> str:
        return self.data.get("llm", {}).get("default_model", "")

    @property
    def default_model(self) -> Optional[dict]:
        """返回当前默认模型的完整配置"""
        name = self.default_model_name
        for m in self.models:
            if m["name"] == name:
                return m
        if self.models:
            return self.models[0]
        return None

    # ── API Key ──

    @property
    def api_keys(self) -> dict:
        """按提供商索引的 API Key 表"""
        return self.data.get("api_keys", {})

    def _get_provider_key(self, provider: str) -> str:
        """获取指定提供商已解析的 API Key"""
        return self.api_keys.get(provider, "")

    def save_api_key(self, provider: str, api_key: str):
        """保存 API Key 到 config.yaml"""
        with open(self._config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if "api_keys" not in raw:
            raw["api_keys"] = {}
        raw["api_keys"][provider] = api_key

        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True)

        # 内存同步
        self.data = raw
        self._resolve_env_vars()

    # ── 价格 ──

    @property
    def pricing_dict(self) -> dict:
        """返回价格字典 {model_name: {input, output}}，仅供 CostTracker 兜底"""
        return {}  # 价格现在由 pricing_fetcher 动态获取

    # ── Agent ──

    @property
    def system_prompt(self) -> str:
        return self.data.get("agent", {}).get("system_prompt", "")

    @property
    def workspace(self) -> str:
        """工作区目录：默认当前终端目录（CWD），可通过 config.yaml 覆盖"""
        return self.data.get("agent", {}).get("workspace", os.getcwd())

    def find_model(self, name: str) -> Optional[dict]:
        for m in self.models:
            if m["name"] == name:
                return m
        return None
