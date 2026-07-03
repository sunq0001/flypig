"""DDD 核心层（Shared Kernel）— 所有业务模块所依赖的纯领域接口

包含：Entity, ValueObject, AggregateRoot, DomainEvent, DomainService,
Repository, EventPublisher, UnitOfWork。

使用方式：from flypig.shared.base import Entity, ValueObject, ...
"""

__all__ = []  # 核心基类由 shared.base 统一导出
