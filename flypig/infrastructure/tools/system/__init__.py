"""系统工具

为什么做：AI 需要执行 shell 命令、管理后台任务等系统级操作。
实现方法：ToolBash 封装 subprocess，ToolTask 管理后台任务生命周期。

层&依赖：infrastructure.tools.system 层
"""

from flypig.infrastructure.tools.system.bash import ToolBash
from flypig.infrastructure.tools.system.task import ToolTaskStatus

__all__ = ["ToolBash", "ToolTaskStatus"]
