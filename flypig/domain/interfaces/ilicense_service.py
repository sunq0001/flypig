"""许可证服务接口

为什么做：商业使用/开源合规需要检查模型许可证，不能硬编码。

实现方法：ILicenseService ABC 定义 check_license() 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod


class ILicenseService(ABC):
    """许可证服务接口 — 模型许可证合规检查"""

    @abstractmethod
    async def check_license(self, model_name: str) -> dict: ...
