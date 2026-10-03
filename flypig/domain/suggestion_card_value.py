"""
建议卡片值对象 — AI 建议的确认/拒绝状态

为什么做：项目遵循「AI 建议、用户决定」，任何模式切换/工具调用都必须落到一张卡片的
        确认或拒绝上，这个状态需要被领域层显式建模。
实现方法：SuggestionCard 保存当前状态标识，通过 is_approved()/approve()/reject()
        暴露状态查询与迁移。
层&依赖：domain 层（值对象），依赖 shared
"""

from flypig.shared.base import ValueObject


class SuggestionCard(ValueObject):
    """建议卡片值对象 — AI 建议的确认/拒绝状态"""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def is_approved(self) -> None:
        """TODO: SuggestionCard.is_approved"""
        return False

    def approve(self) -> None:
        """TODO: SuggestionCard.approve"""
        pass

    def reject(self) -> None:
        """TODO: SuggestionCard.reject"""
        pass
