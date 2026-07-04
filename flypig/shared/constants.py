"""跨层共享常量

为什么做：避免同一常量在多个文件中重复定义，改一处漏三处。

| 层级 | 位置 | 示例 |
|------|------|------|
| 文件级 | 各文件头部 | `PORTKEY_REQUEST_TIMEOUT` 只在 pricing.py 用 |
| 层  级 | shared/constants.py | HTTP 状态码、SSE 事件类型等被多层使用 |
| 配置级 | config.yaml | 可能被运维改的值 |

实现方法：模块级常量定义，按用途分组，文件级/层级/配置级三级体系。

使用方式：
    from shared.constants import SSE_EVENT_TEXT_DELTA

注意：HTTP 状态码优先使用标准库 from http import HTTPStatus。

层&依赖：shared 层，零依赖
"""

# ── SSE 事件类型 ──
SSE_EVENT_ERROR = "error"
SSE_EVENT_TEXT_START = "text-start"
SSE_EVENT_TEXT_DELTA = "text-delta"
SSE_EVENT_TEXT_END = "text-end"
SSE_EVENT_FINISH = "finish"

# ── 通用截断长度 ──
ERROR_TRUNCATE_LENGTH = 200

# ── 队列容量 ──
MAX_QUEUE_SIZE = 500
