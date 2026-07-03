"""工作区聚合根

为什么做：AI Agent 在项目目录中操作文件/执行命令，需要 workspace 聚合管理项目元数据。
实现方法：Workspace(AggregateRoot) 包含路径、文件列表、配置等。

层&依赖：domain 层，依赖 shared
"""

from flypig.shared.base import AggregateRoot


class Workspace(AggregateRoot):
    """工作区聚合根 — 管理项目/目录级别的元数据和配置"""
    pass
