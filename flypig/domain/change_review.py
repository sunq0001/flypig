"""变更审查实体

为什么做：AI 每次修改代码需要记录审查结果（审批状态/风险等级/评论）。
实现方法：ChangeReview(Entity) 包含 review_id, change_score, status, reviewer, comments。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import Entity


class ChangeReview(Entity):
    """变更审查实体 — 每次代码修改的审查记录"""

    pass
