"""本地模型服务接口

为什么做：domain 层需要定义"怎么查询本地模型状态/拉取模型"的契约，
但不应直接依赖 Ollama HTTP 的具体实现（当前在 acl/ollama.py）。

层&依赖：domain.interfaces 层，depends on nothing
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
