"""检查每个 domain/interfaces 的 ABC 在 infrastructure 中是否有实现"""
import ast
from pathlib import Path

infra = Path("flypig/infrastructure")
interfaces = Path("flypig/domain/interfaces")

for f in sorted(interfaces.rglob("*.py")):
    if f.name == "__init__.py":
        continue
    tree = ast.parse(f.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            is_abc = any(
                isinstance(b, ast.Name) and b.id == "ABC" for b in node.bases
            )
            if is_abc:
                name = node.name
                impls = []
                for pyf in sorted(infra.rglob("*.py")):
                    if pyf.name == "__init__.py":
                        continue
                    content = pyf.read_text(encoding="utf-8")
                    if name not in content:
                        continue
                    t2 = ast.parse(content)
                    for n2 in ast.walk(t2):
                        if isinstance(n2, ast.ClassDef):
                            bases = [
                                b.id for b in n2.bases if isinstance(b, ast.Name)
                            ]
                            if name in bases:
                                impls.append(f"{pyf.name}>{n2.name}")
                if not impls:
                    print(f"  [MISS] {name} ({f.name})")
