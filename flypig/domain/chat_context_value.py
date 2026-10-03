"""对话上下文值对象

为什么做：封装当前对话的上下文数据，供 AI 推理参考。
实现方法：ChatContext(ValueObject) 包含 context_id 和数据字典。

TODO: 填充业务方法后移除 __init__ 中字段定义

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class ChatContext(ValueObject):
    """对话上下文值对象 — 封装当前对话的上下文数据"""

    def __init__(self, value: str = "") -> None:
        self._value = value

    def is_valid(self) -> None:
        """TODO: ChatContext.is_valid"""
        pass

    def to_dict(self) -> None:
        """TODO: ChatContext.to_dict"""
        pass

    def merge(self) -> None:
        """TODO: ChatContext.merge"""
        pass
