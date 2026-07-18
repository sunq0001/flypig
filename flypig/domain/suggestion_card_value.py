"""
建议卡片值对象 — AI 建议的确认/拒绝状态

TODO: 填充业务方法后移除 __init__ 中字段定义

层&依赖：domain 层，依赖 shared
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
