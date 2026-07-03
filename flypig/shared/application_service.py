"""应用服务基类 — 编排领域逻辑

职责：接收应用请求 → 调用 DomainService 和 Repository → 管理事务 → 发布领域事件。
不含业务逻辑，只做协调编排。

层&依赖：shared 层，零依赖
"""

from abc import ABC


class ApplicationService(ABC):
    """应用服务基类 — 编排领域逻辑

    职责：
        - 接收应用层请求（DTO/命令）
        - 调用 DomainService 和 Repository 完成业务
        - 管理 UnitOfWork 的事务边界
        - 发布领域事件

    约束：
        - 不含业务逻辑（业务逻辑在 DomainService 或 AggregateRoot 中）
        - 只做协调和编排
    """
    pass
