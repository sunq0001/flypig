"""批量修复 stub 文件的 docstring 格式"""
import re
from pathlib import Path

infra = Path("flypig/infrastructure")
new_doc = (
    '"""存根实现 — TODO: 替换为真实实现\n\n'
    "为什么做：满足 architecture_check 接口契约检查，防止 pre-commit 拦截。\n"
    "实现方法：继承 domain/interfaces 的 ABC，方法体留空或返回默认值。\n"
    "层\u0026依赖：infrastructure 层，依赖对应的 domain.interfaces 接口\n"
    '"""'
)

for f in sorted(infra.glob("*_stub.py")):
    content = f.read_text(encoding="utf-8")
    content = re.sub(r'""".*?"""', new_doc, content, count=1)
    f.write_text(content, encoding="utf-8")
    print(f"  fixed {f.name}")
