"""模型映射器接口

为什么做：不同厂商的模型名/参数/定价需要互相映射转换。

实现方法：IMapper ABC 定义 map_model() 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class IMapper(ABC):
    """模型映射器接口 — 跨厂商模型名/参数映射"""

    @abstractmethod
    async def map_model(self, model_name: str, target_provider: str) -> dict[str, Any]: ...
