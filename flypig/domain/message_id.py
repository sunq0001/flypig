"""兼容导入 — MessageId 定义在 message.py 中

为什么做：保持从 domain.message_id 导入的旧代码兼容性，实际实现已在 message.py 中。

实现方法：re-export，从 flypig.domain.message 导入 MessageId。

层&依赖：domain 层
"""
from flypig.domain.message import MessageId  # noqa: F401
