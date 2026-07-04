"""__init__

为什么做：DDD 核心层 — Shared Kernel，所有业务模块依赖的纯领域接口

实现方法：import + re-export DDD 基类，由 shared.base 统一对外导出

层&依赖：shared.kernel 层
"""

__all__ = []  # 核心基类由 shared.base 统一导出
