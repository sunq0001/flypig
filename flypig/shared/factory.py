"""factory

为什么做：工厂基类，封装复杂创建逻辑

实现方法：ABC + Generic[T]，定义 create 抽象方法

层&依赖：shared 层
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Factory(ABC, Generic[T]):
    """工厂基类 — 封装复杂创建逻辑

    用于以下场景：
        - 创建需要复杂装配的聚合根
        - 根据策略创建不同的实现（如 ModelFactory）
        - 从外部数据重构领域对象

    约束：
        - 返回完整的领域对象
        - 不处理持久化（那是 Repository 的事）
    """

    @abstractmethod
    def create(self, *args, **kwargs) -> T:
        """创建一个领域对象"""
        ...
