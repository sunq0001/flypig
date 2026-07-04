"""兼容导入 — SessionStatus 定义在 session.py 中

为什么做：保持从 domain.session_status 导入的旧代码兼容性。

实现方法：re-export，从 flypig.domain.session 导入 SessionStatus。

层&依赖：domain 层
"""
from flypig.domain.session import SessionStatus  # noqa: F401
