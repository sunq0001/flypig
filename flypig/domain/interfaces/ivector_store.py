"""向量存储接口

为什么做：语义搜索/RAG 需要向量数据库的统一存取接口。

实现方法：IVectorStore ABC 定义 upsert/search 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class IVectorStore(ABC):
    """向量存储接口 — 向量嵌入的存取与搜索"""

    @abstractmethod
    async def upsert(self, vectors: list[dict[str, Any]]) -> None: ...

    @abstractmethod
    async def search(self, query_vector: list[float], top_k: int = 10) -> list[dict[str, Any]]: ...
