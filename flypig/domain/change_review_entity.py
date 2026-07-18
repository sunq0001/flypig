"""代码审查实体

为什么做：AI 对代码变更进行审查，需要记录审查结果和建议。
实现方法：ChangeReview(Entity) 封装变更文件路径/建议/评分。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import Entity


class ChangeReview(Entity):
    """代码审查实体 — AI 对变更的审查结果"""

    def __init__(self, file_path: str, suggestion: str, score: float = 0.0) -> None:
        self._file_path = file_path
        self._suggestion = suggestion
        self._score = score

    @property
    def score(self) -> float:
        return self._score

    def is_approved(self) -> bool:
        """TODO: 判断审查是否通过"""
        return self._score >= 0.7

    def to_suggestion_card(self) -> dict:
        """TODO: 转换为前端建议卡片格式"""
        ...
