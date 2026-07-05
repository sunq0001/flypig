"""知识图谱接口

为什么做：项目结构/代码关系的语义搜索需要图数据库支持，提供统一查询入口。

实现方法：IKnowledgeGraph ABC 定义 query/upsert 方法。

层&依赖：domain.interfaces 层，零依赖
TODO: 骨架文件，待实现具体方法
"""

from abc import ABC, abstractmethod
from typing import Any


class IKnowledgeGraph(ABC):
    """知识图谱接口 — 项目知识的图查询"""

    @abstractmethod
    async def query(self, query: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def upsert(self, nodes: list[dict], edges: list[dict]) -> None: ...
