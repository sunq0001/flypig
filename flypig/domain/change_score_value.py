"""
变更等级值对象 — 代码变更的影响等级与评分

为什么做：对抗审查系统需要把连续的变更评分映射成离散等级（info/warning/critical），
        把「多低算高危」这类阈值规则收敛到领域层，避免各调用方各自拍数字。
实现方法：ChangeLevel 封装等级字符串并提供 from_score() 按分数区间映射；
        ChangeScore 封装分值并提供 is_high_risk() 判断（两者共用同一组阈值常量）。
层&依赖：domain 层（值对象），仅依赖 shared
"""

from flypig.shared.base import ValueObject

# ── 等级阈值（低于该分数即归入对应风险等级）──
_CRITICAL_THRESHOLD = 0.3
_WARNING_THRESHOLD = 0.6


class ChangeLevel(ValueObject):
    """变更等级值对象（info / warning / critical）"""

    def __init__(self, level: str = "info") -> None:
        self._level = level

    @classmethod
    def from_score(cls, score: float) -> "ChangeLevel":
        """按变更分数映射等级：<0.3 高危，<0.6 警告，其余 info"""
        if score < _CRITICAL_THRESHOLD:
            return cls("critical")
        if score < _WARNING_THRESHOLD:
            return cls("warning")
        return cls("info")

    @property
    def level(self) -> str:
        """等级字符串（info/warning/critical）"""
        return self._level

    def __str__(self) -> str:
        return self._level


class ChangeScore(ValueObject):
    """变更评分值对象（0.0~1.0，越低越危险）"""

    def __init__(self, score: float = 0.0) -> None:
        self._score = score

    @property
    def score(self) -> float:
        return self._score

    def is_high_risk(self) -> bool:
        """是否达到高危阈值"""
        return self._score < _CRITICAL_THRESHOLD
