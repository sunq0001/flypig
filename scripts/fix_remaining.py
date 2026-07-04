"""修复新文件中的可修违规"""
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "flypig"

# 1. chat_response.py - to_sse 的 import json 移到文件顶部
p = BASE / "application" / "dto" / "chat_response.py"
c = p.read_text(encoding="utf-8")
c = c.replace(
    "from typing import Any, Dict, List, Optional",
    "import json\nfrom typing import Any, Dict, List, Optional",
)
c = c.replace(
    '        import json\n        payload: Dict[str, Any] = {"type": self.type}',
    '        payload: Dict[str, Any] = {"type": self.type}',
)
p.write_text(c, encoding="utf-8")
print("fixed: chat_response.py (import json top)")

# 2. files_routes.py - send_file 移到文件顶部
p = BASE / "interface" / "rest" / "routes" / "files_routes.py"
c = p.read_text(encoding="utf-8")
c = c.replace(
    "from quart import Blueprint, request, Response, jsonify",
    "from quart import Blueprint, request, Response, jsonify, send_file",
)
c = c.replace(
    '    """发送图片文件（原始二进制，不走 JSON）"""\n    from quart import send_file\n    return await send_file',
    '    """发送图片文件（原始二进制，不走 JSON）"""\n    return await send_file',
)
p.write_text(c, encoding="utf-8")
print("fixed: files_routes.py (send_file top)")

# 3. test_pricing_entry.py - import pytest 移到文件顶部
p = BASE / "tests" / "unit" / "test_pricing_entry.py"
c = p.read_text(encoding="utf-8")
c = c.replace(
    "from flypig.domain import PricingEntry",
    "import pytest\nfrom flypig.domain import PricingEntry",
)
c = c.replace(
    '        import pytest\n        entry = PricingEntry(input_price=1.0, output_price=2.0)',
    '        entry = PricingEntry(input_price=1.0, output_price=2.0)',
)
p.write_text(c, encoding="utf-8")
print("fixed: test_pricing_entry.py (pytest top)")

# 4. shared/constants.py - 补 docstring 段落
p = BASE / "shared" / "constants.py"
c = p.read_text(encoding="utf-8")
c = c.replace(
    "使用方式：\n    from shared.constants import SSE_EVENT_TEXT_DELTA",
    "实现方法：模块级常量定义，按用途分组，文件级/层级/配置级三级体系。\n\n使用方式：\n    from shared.constants import SSE_EVENT_TEXT_DELTA",
)
p.write_text(c, encoding="utf-8")
print("fixed: shared/constants.py (docstring)")

print("\nAll done!")
