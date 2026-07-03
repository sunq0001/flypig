"""ModelFactory 实现 — 根据模型名创建对应的 IModel 适配器

层&依赖：infrastructure.llm 层，实现 domain.interfaces.imodel_factory.IModelFactory
"""

from __future__ import annotations

from typing import Optional

from flypig.shared.settings import AppSettings
from flypig.domain.interfaces.imodel import IModel
from flypig.domain.interfaces.imodel_factory import IModelFactory
from flypig.domain.registry import ModelRegistry
from flypig.infrastructure.llm.openai_adapter import OpenAIAdapter


class ModelFactory(IModelFactory):
    """模型工厂 — 按模型名路由到对应的适配器实现"""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def create(
        self,
        model_name: str,
        settings: Optional[AppSettings] = None,
    ) -> IModel:
        meta = self._registry.resolve(model_name)
        provider = (meta or {}).get("provider", "")

        if provider == "Anthropic":
            # TODO: 后续加入 AnthropicAdapter
            pass

        return OpenAIAdapter(model_name, settings, registry=self._registry)
