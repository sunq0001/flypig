"""__init__

为什么做：防腐层（ACL）隔离外部系统格式对领域层的污染，将所有外部格式翻译为领域对象

实现方法：纯函数转换，输入外部 JSON → 输出领域 ValueObject。每个外部系统一个文件

层&依赖：acl 层
"""

from flypig.acl.pricing import default_pricing_to_entry, portkey_to_pricing_entry

__all__ = [
    "default_pricing_to_entry",
    "portkey_to_pricing_entry",
]
