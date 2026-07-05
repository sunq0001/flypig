"""Specification — 按状态过滤会话

为什么做：查询 session list 时经常需要按 active/archived/closed 状态过滤。
实现方法：SessionByStatus(Specification[Session])，通过 DI 注入。

层&依赖：domain.specification 层，依赖 shared.Specification + domain.session
"""

from flypig.domain.session import Session
from flypig.shared.base import Specification


class SessionByStatus(Specification[Session]):
    """按会话状态过滤规格"""

    def is_satisfied_by(self, candidate: Session) -> bool:
        """TODO: 判断候选会话是否匹配指定状态"""
        return True
