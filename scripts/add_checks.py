"""向 architecture_check.py 注入新检查器"""
import re
from pathlib import Path

path = Path(__file__).resolve().parent / "architecture_check.py"
content = path.read_text(encoding="utf-8")

# 新检查器代码
new_checks = r'''
def check_robust_async(file_path: Path) -> list[str]:
    """检查 async 私有函数是否有 try 保护"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                continue
            has_await = any(isinstance(n, ast.Await) for n in ast.walk(node))
            has_try = any(isinstance(n, ast.Try) for n in ast.walk(node))
            if has_await and not has_try:
                violations.append(f"  [ROBUST] {node.name} 有 await 但无 try/except")
                break
    return violations


def check_robust_fileio(file_path: Path) -> list[str]:
    """检查文件操作是否有 try 保护"""
    violations: list[str] = []
    if "test_" in file_path.name:
        return violations
    content = file_path.read_text(encoding="utf-8")
    if not any(kw in content for kw in ("open(", ".read_text(", ".write_text(")):
        return violations
    if "try:" in content:
        return violations
    tree = read_tree(file_path)
    if tree is None:
        return violations
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in ("open", "read_text", "write_text"):
                violations.append(f"  [ROBUST] 文件操作 ({func.attr}) 没有 try 包裹")
                break
    return violations


def check_perf_import(file_path: Path) -> list[str]:
    """检查函数内 import（多次调用重复加载）"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for inner in ast.walk(node):
                if isinstance(inner, (ast.Import, ast.ImportFrom)):
                    violations.append(f"  [PERF] 函数 {node.name} 内有 import，应提到文件顶部")
                    return violations
    return violations


def check_couple_pkg(file_path: Path) -> list[str]:
    """检查包级别耦合度"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations
    layers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                pkg = get_imported_package(alias.name)
                if pkg:
                    layers.add(pkg)
        elif isinstance(node, ast.ImportFrom) and node.module:
            pkg = get_imported_package(node.module)
            if pkg:
                layers.add(pkg)
    if len(layers) > 2:
        violations.append(f"  [COUPLE_PKG] 依赖了 {len(layers)} 个包 ({', '.join(sorted(layers))})")
    return violations
'''

# 在 REQUIRED_DOC_SECTIONS 前插入
marker = 'REQUIRED_DOC_SECTIONS = ["为什么做", "实现方法", "层&依赖"]'
content = content.replace(marker, new_checks + "\n\n" + marker)

# 注册检查器
reg_marker = '("docq",     "docstring质量",       check_docstring_quality),'
reg_new = '''        ("robust",   "IO无try保护",         check_robust_async),
        ("robustio", "文件无try保护",        check_robust_fileio),
        ("perf",     "函数内import",         check_perf_import),
        ("couplepkg","包耦合度过高",         check_couple_pkg),
        ("docq",     "docstring质量",       check_docstring_quality),'''
content = content.replace(reg_marker, reg_new)

# 添加标签
label_marker = '"docq":     ("DOCQ",     "docstring质量"),'
label_new = '''        "robust":   ("ROBUST",   "IO无try保护"),
        "robustio": ("ROBUSTIO", "文件无try保护"),
        "perf":     ("PERF",     "函数内import"),
        "couplepkg":("COUPLE_PKG","包耦合度过高"),
        "docq":     ("DOCQ",     "docstring质量"),'''
content = content.replace(label_marker, label_new)

path.write_text(content, encoding="utf-8")
print("Done - 4 new checks injected")
