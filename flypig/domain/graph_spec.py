"""图谱规格值对象

为什么做：LangGraph 的 StateGraph 配置需要统一描述（节点/边/条件路由）。
实现方法：GraphSpec(ValueObject) 描述图的拓扑结构。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import ValueObject


class GraphSpec(ValueObject):
    """LangGraph 图谱规格值对象"""

    pass
