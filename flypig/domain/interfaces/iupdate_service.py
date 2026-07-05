"""更新服务接口

为什么做：应用自动更新/检查新版本需要统一接口，支持不同更新源。

实现方法：IUpdateService ABC 定义 check_update() 和 apply_update() 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod


class IUpdateService(ABC):
    """更新服务接口 — 应用版本检查和更新"""

    @abstractmethod
    async def check_update(self) -> dict: ...

    @abstractmethod
    async def apply_update(self) -> bool: ...
