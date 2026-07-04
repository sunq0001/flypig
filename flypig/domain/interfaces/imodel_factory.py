"""imodel_factory

为什么做：路由层不应直接 new OpenAIAdapter，应通过工厂接口创建模型适配器

实现方法：Factory[IModel] 泛型，create 方法接收模型名 + 配置，返回对应的 IModel 实例

层&依赖：domain.interfaces 层，extends Factory[IModel]
"""

from __future__ import annotations

from typing import Any, Optional

from flypig.domain.interfaces.imodel import IModel
from flypig.shared.base import Factory


class IModelFactory(Factory[IModel]):
    """模型工厂接口 — 根据模型名创建对应的 IModel 适配器"""

    def create(  # type: ignore[override]
        self,
        model_name: str,
        settings: Any = None,
    ) -> IModel:
        """根据模型名创建适配器

        Args:
            model_name: 模型名（如 deepseek-v4-flash）
            settings: 应用配置（用于获取 API Key 等）

        Returns:
            对应的 IModel 实现实例

        Raises:
            ModelAPIError: 配置缺失或创建失败
        """
        ...
