"""application_service

为什么做：应用服务基类，定义编排层的行为契约

实现方法：ABC 标记基类，约束：不含业务逻辑，只做协调和编排

层&依赖：shared 层
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
