"""base

为什么做：统一导出入口，所有领域层的共享基类和接口集中在此导出

实现方法：从 shared/kernel 和各模块 re-export，业务模块只需 from flypig.shared.base import Entity

层&依赖：shared 层
"""

from flypig.shared.application_service import ApplicationService
from flypig.shared.factory import Factory
from flypig.shared.kernel.aggregate_root import AggregateRoot
from flypig.shared.kernel.domain_event import DomainEvent
from flypig.shared.kernel.domain_service import DomainService
from flypig.shared.kernel.entity import Entity
from flypig.shared.kernel.event_bus import EventPublisher
from flypig.shared.kernel.repository import Repository
from flypig.shared.kernel.unit_of_work import UnitOfWork
from flypig.shared.kernel.value_object import ValueObject
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
