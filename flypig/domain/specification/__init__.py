"""规格模式包 — 可组合的业务规则

使用方式：
    from flypig.domain.specification import SessionByStatus, SessionByTime
"""

from flypig.domain.specification.session_by_status import SessionByStatus
from flypig.domain.specification.session_by_time import SessionByTime
from flypig.domain.specification.session_by_user import SessionByUser

__all__ = [
    "SessionByStatus",
    "SessionByTime",
    "SessionByUser",
]
