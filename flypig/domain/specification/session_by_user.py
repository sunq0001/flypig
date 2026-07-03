"""Specification — 按用户过滤会话

为什么做：多用户场景下需要按用户过滤可见的会话列表。
实现方法：SessionByUser(Specification[Session])，通过 user_id 匹配。

层&依赖：domain.specification 层，依赖 shared.Specification + domain.session
"""

from flypig.shared.base import Specification
from flypig.domain.session import Session


class SessionByUser(Specification[Session]):
    """按用户过滤会话规格"""
    def is_satisfied_by(self, candidate: Session) -> bool:
        """TODO: 判断候选会话是否属于指定用户"""
        return True
