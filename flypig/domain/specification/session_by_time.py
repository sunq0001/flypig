"""Specification — 按时间范围过滤会话

为什么做：查询 session list 时需要按创建时间/最后活动时间做范围过滤。
实现方法：SessionByTime(Specification[Session])，支持 start_time / end_time。

层&依赖：domain.specification 层，依赖 shared.Specification + domain.session
"""

from flypig.shared.base import Specification
from flypig.domain.session import Session


class SessionByTime(Specification[Session]):
    """按时间范围过滤会话规格"""
    def is_satisfied_by(self, candidate: Session) -> bool:
        """TODO: 判断候选会话是否在指定时间范围内"""
        return True
