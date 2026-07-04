"""ilocal_model_service

为什么做：本地模型（Ollama）的管理操作（检测运行状态、列表已安装模型、拉取模型）需要统一接口，方便测试和替换

实现方法：ABC 定义 check_running / list_installed_names / pull_model 三个方法。OllamaLocalModelService 实现基于 httpx

层&依赖：domain.interfaces 层
"""

from abc import ABC, abstractmethod


class ILocalModelService(ABC):
    """本地模型（Ollama）服务接口"""

    @abstractmethod
    async def check_running(self) -> bool:
        """检查 Ollama 服务是否运行中"""
        ...

    @abstractmethod
    async def list_models(self) -> list[dict]:
        """获取已安装模型列表（含缓存）

        Returns:
            每个 dict 含 name / provider / base_url / api_model / local / has_key
        """
        ...

    @abstractmethod
    async def list_installed_names(self) -> list[str]:
        """获取已安装模型名称列表"""
        ...

    @abstractmethod
    async def pull_model(self, model_name: str) -> None:
        """后台拉取指定模型"""
        ...
