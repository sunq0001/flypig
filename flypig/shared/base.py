"""DDD 基类定义 — 统一导出入口

所有领域层的共享基类和接口集中在此文件导出，
业务模块只需 `from flypig.shared.base import ...` 即可。

包含：
    - ValueObject:     值对象，不可变，按值相等         (kernel/)
    - Entity:          实体，有唯一标识，按 ID 相等      (kernel/)
    - AggregateRoot:   聚合根，管理内部实体和领域事件    (kernel/)
    - DomainEvent:     领域事件基类                     (kernel/)
    - Repository:      仓储接口泛型                     (kernel/)
    - DomainService:   领域服务标记基类                  (kernel/)
    - EventPublisher:  事件发布器接口                   (kernel/)
    - UnitOfWork:      工作单元接口                     (kernel/)
    - Factory:         工厂基类
    - ApplicationService: 应用服务基类
    - Result:          结果类型
    - ValidationResult / Validator: 校验
    - Specification:   规格模式
"""

from flypig.shared.kernel.aggregate_root import AggregateRoot
from flypig.shared.kernel.domain_event import DomainEvent
from flypig.shared.kernel.domain_service import DomainService
from flypig.shared.kernel.entity import Entity
from flypig.shared.kernel.event_bus import EventPublisher
from flypig.shared.kernel.repository import Repository
from flypig.shared.kernel.unit_of_work import UnitOfWork
from flypig.shared.kernel.value_object import ValueObject

from flypig.shared.application_service import ApplicationService
from flypig.shared.factory import Factory
from flypig.shared.result import Result
from flypig.shared.specification import (
    AndSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
)
from flypig.shared.validation import ValidationResult, Validator

__all__ = [
    "AggregateRoot",
    "AndSpecification",
    "ApplicationService",
    "DomainEvent",
    "DomainService",
    "Entity",
    "EventPublisher",
    "Factory",
    "NotSpecification",
    "OrSpecification",
    "Repository",
    "Result",
    "Specification",
    "UnitOfWork",
    "ValidationResult",
    "Validator",
    "ValueObject",
]
