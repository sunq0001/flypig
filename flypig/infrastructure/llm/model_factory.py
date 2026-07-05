"""model_factory

为什么做：根据模型名路由到对应的适配器实现

实现方法：ModelFactory 实现 IModelFactory 接口，按 provider 路由：Anthropic → AnthropicAdapter，其他 → OpenAIAdapter

层&依赖：infrastructure.llm 层，实现 domain.interfaces.imodel_factory
"""

from __future__ import annotations

from flypig.domain.interfaces.imodel import IModel
from flypig.domain.interfaces.imodel_factory import IModelFactory
from flypig.domain.registry import ModelRegistry
from flypig.infrastructure.llm.openai_adapter import OpenAIAdapter
from flypig.shared.settings import AppSettings


class ModelFactory(IModelFactory):
    """模型工厂 — 按模型名路由到对应的适配器实现"""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def create(
        self,
        model_name: str,
        settings: AppSettings | None = None,
    ) -> IModel:
        meta = self._registry.resolve(model_name)
        provider = (meta or {}).get("provider", "")

        if provider == "Anthropic":
            pass  # TODO: 后续加入 AnthropicAdapter（占位符标记）

        return OpenAIAdapter(model_name, settings, registry=self._registry)
