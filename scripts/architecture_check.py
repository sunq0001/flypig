#!/usr/bin/env python3
"""FlyPig 架构合规检查 — 守护 DDD 分层边界

检查项：
  1. LAYER    — 层依赖方向（domain → application → infrastructure → interface）
  2. DDD      — DDD 基类继承（domain 层的类必须继承 Entity/ValueObject 等）
  3. WILD     — 不允许 import *（通配导入）
  4. DOC      — 每个 .py 文件必须有文件级 docstring
  5. ALL      — 每个 __init__.py 必须有 __all__
  6. EXC      — 禁止抛裸 Exception / RuntimeError
  7. SIZE     — 单个文件不超过 300 行
  8. SKEL     — 骨架文件必须有 TODO 标记
  9. COUPLE   — import 过多（>25条），提示高耦合
  10. PARAMS   — 函数参数过多（>6个），提示不单一职责
  11. HARDCODE — 硬编码 URL / 密钥，提示应放入配置文件
  12. NESTING  — 嵌套深度 >4 层，提示复杂度高
  13. MAGIC    — 魔法数字，建议定义为命名常量
  14. EMPTY_EXC— 裸 except / except:pass，禁止静默吞异常
  15. LONGFUNC — 函数体 >50 行/ >80 行警告，建议拆分
  16. TODO     — 非骨架文件遗留 TODO/FIXME 标记
  17. PRINT    — 生产代码中的 print()，应使用 logger
  18. ASSERT   — 生产代码中的 assert，应使用显式异常
  19. DOCQ     — docstring 质量：domain 层必须标注 DDD 类型
  20. CIRCULAR — 循环依赖检测（A → B → C → A）

用法：
    python scripts/architecture_check.py

退出码：
    0 = 全部通过
    1 = 有违规
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# ── 层级定义 ──
LAYER_RULES: dict[str, list[str]] = {
    "domain":         ["shared", "domain"],
    "application":    ["shared", "domain", "application", "bootstrap"],
    "infrastructure": ["shared", "domain", "application", "infrastructure", "bootstrap", "acl"],
    "interface":      ["shared", "domain", "application", "infrastructure", "interface", "bootstrap"],
    "bootstrap":      ["shared", "domain", "application", "infrastructure", "interface", "bootstrap"],
    "orchestration":  ["shared", "domain", "application", "infrastructure", "orchestration", "bootstrap"],
    "acl":            ["shared", "domain", "acl"],
}

# 跳过检查的目录
SKIP_DIRS = {
    "__pycache__", ".mypy_cache", ".pytest_cache",
    "migrations", "chat-server", "web", "desktop", "electron",
}

# domain 层中跳过 DDD 继承检查的子目录
DDD_SKIP_SUBDIRS = {"interfaces", "event", "specification", "prompts"}

# DDD 基类白名单
DDD_BASE_CLASSES = {
    "Entity", "ValueObject", "AggregateRoot", "DomainEvent",
    "DomainService", "ApplicationService", "Repository",
    "Specification", "Factory", "ABC",
    "Enum", "TypedDict", "Protocol",
}

# 文件行数阈值
MAX_LINES = 300

# 标记为"已知硬编码"的合法模式（不报错）
ALLOWED_HARDCODE_PATTERNS = [
    r"https://api\.deepseek\.com",
    r"https://api\.openai\.com",
    r"https://api\.anthropic\.com",
    r"http://localhost:\d+",
    r"http://127\.0\.0\.1:\d+",
]


def get_layer(file_path: Path, base_dir: Path) -> str | None:
    try:
        rel = file_path.relative_to(base_dir)
        parts = rel.parts
        return parts[1] if len(parts) >= 2 else None
    except ValueError:
        return None


def get_imported_package(import_str: str) -> str | None:
    if not import_str.startswith("flypig."):
        return None
    parts = import_str.split(".")
    return parts[1] if len(parts) >= 2 else None


def read_tree(file_path: Path) -> ast.AST | None:
    try:
        return ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _inherits_from(node: ast.ClassDef, class_names: set[str]) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in class_names:
            return True
        if isinstance(base, ast.Attribute) and base.attr in class_names:
            return True
    return False


def _has_todo(content: str) -> bool:
    return "TODO" in content or "FIXME" in content or "HACK" in content


# ══════════════════════════════════════════════════════════════
# 检查器函数
# ══════════════════════════════════════════════════════════════

def check_layer(file_path: Path, base_dir: Path) -> list[str]:
    """检查层依赖方向"""
    violations: list[str] = []
    source_layer = get_layer(file_path, base_dir)
    if not source_layer or source_layer not in LAYER_RULES:
        return violations

    allowed = LAYER_RULES[source_layer]
    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                pkg = get_imported_package(alias.name)
                if pkg and pkg not in allowed and pkg != source_layer:
                    violations.append(f"  [LAYER] 位于 {source_layer} 层，但 import 了 {pkg} 层（{alias.name}）")
        elif isinstance(node, ast.ImportFrom) and node.module:
            pkg = get_imported_package(node.module)
            if pkg and pkg not in allowed and pkg != source_layer:
                names = [n.name for n in node.names]
                violations.append(
                    f"  [LAYER] 位于 {source_layer} 层，但 from {pkg} 层 import {', '.join(names)}"
                )
    return violations


def check_ddd_inheritance(file_path: Path) -> list[str]:
    """检查 domain 层类是否继承 DDD 基类"""
    violations: list[str] = []
    if file_path.name == "__init__.py" or file_path.name.endswith("_handler.py"):
        return violations
    for skip in DDD_SKIP_SUBDIRS:
        if skip in file_path.parts:
            return violations

    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        return violations

    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if _is_skeleton_class(node):
                continue
            if node.name.endswith(("Error", "Exception")) or _inherits_from(node, {"Exception", "BaseException"}):
                continue
            if _inherits_from(node, {"TypedDict", "Enum", "Protocol"}):
                continue

            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            if not any(b in DDD_BASE_CLASSES for b in bases):
                violations.append(
                    f"  [DDD] {file_path.name} 中的类 {node.name} 没有继承 DDD 基类"
                )
    return violations


def check_wildcard(file_path: Path) -> list[str]:
    """检查通配导入"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.names and any(n.name == "*" for n in node.names):
            violations.append(f"  [WILD] 使用了 from {node.module} import *")
    return violations


def check_docstring(file_path: Path) -> list[str]:
    """检查文件级 docstring（__init__.py 放宽为必须有注释）"""
    violations: list[str] = []
    content = file_path.read_text(encoding="utf-8")
    stripped = content.strip()
    if not stripped:
        return violations  # 空文件占位符

    tree = read_tree(file_path)
    if tree is None:
        return violations

    docstring = ast.get_docstring(tree)
    if not docstring:
        # __init__.py 允许没有 docstring 但必须有至少一句注释或 __all__
        if file_path.name == "__init__.py":
            if "__all__" not in content:
                violations.append("  [DOC] __init__.py 缺少文件级 docstring 或 __all__")
        else:
            violations.append(f"  [DOC] 缺少文件级 docstring")
    return violations


def check_all_export(file_path: Path) -> list[str]:
    """检查 __init__.py 必须有 __all__"""
    violations: list[str] = []
    if file_path.name != "__init__.py":
        return violations

    content = file_path.read_text(encoding="utf-8")
    if "__all__" not in content:
        violations.append("  [ALL] __init__.py 缺少 __all__ 定义")
    return violations


def check_bare_exception(file_path: Path) -> list[str]:
    """检查禁止抛裸 Exception/RuntimeError"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            exc = node.exc
            if exc is not None:
                if isinstance(exc, ast.Call):
                    func = exc.func
                    if isinstance(func, ast.Name) and func.id in ("Exception", "RuntimeError", "BaseException"):
                        violations.append(
                            f"  [EXC] 抛裸 {func.id}()，应使用 FlyPigException 子类"
                        )
    return violations


def check_file_size(file_path: Path) -> list[str]:
    """检查文件行数不超过阈值"""
    violations: list[str] = []
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if len(lines) > MAX_LINES:
        violations.append(f"  [SIZE] 文件 {len(lines)} 行，超过 {MAX_LINES} 行阈值，建议拆分")
    return violations


def check_skeleton_marker(file_path: Path) -> list[str]:
    """骨架文件（只有 docstring + pass）必须有 TODO 标记"""
    violations: list[str] = []
    if file_path.name == "__init__.py":
        return violations

    content = file_path.read_text(encoding="utf-8")
    stripped = content.strip()
    if not stripped:
        return violations

    tree = read_tree(file_path)
    if tree is None:
        return violations

    docstring = ast.get_docstring(tree)
    has_todo = _has_todo(content)

    # 检查是否骨架：只有 docstring 且没有 import/class/def（空文件或仅注释）
    has_code = False
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign)):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue  # docstring
            has_code = True
            break

    if not has_code and docstring and not has_todo:
        violations.append("  [SKEL] 骨架文件（只有 docstring）缺少 TODO 标记，AI 可能误删")


def _is_skeleton_class(node: ast.ClassDef) -> bool:
    """判断是否骨架类（只有 docstring + pass）"""
    body = node.body
    if len(body) == 0:
        return True
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return True
    if len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        return True
    if len(body) == 2 and isinstance(body[0], ast.Expr) and isinstance(body[1], ast.Pass):
        return isinstance(body[0].value, ast.Constant)
    return False


# ── 循环依赖检测 ──

def _module_key(file_path: Path, base_dir: Path) -> str | None:
    """将文件路径转为模块键名（如 flypig.domain.session）"""
    try:
        rel = file_path.relative_to(base_dir.parent)
        parts = list(rel.parts)
        # 去掉 .py 后缀
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        # __init__.py → 包名
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            return None
        return ".".join(parts)
    except ValueError:
        return None


def _extract_flypig_imports(file_path: Path) -> list[str]:
    """提取一个文件中对 flypig 子模块的所有 import 目标"""
    targets: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return targets

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("flypig."):
                    targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            module = node.module
            if module.startswith("flypig."):
                targets.append(module)
    return targets


def check_circular(py_files: list[Path], base_dir: Path) -> list[str]:
    """构建 import 依赖图并检测循环依赖"""
    violations: list[str] = []

    # ── 构建 key 映射 ──
    key_to_path: dict[str, Path] = {}
    for f in py_files:
        key = _module_key(f, base_dir)
        if key:
            key_to_path[key] = f

    # ── 构建依赖图 ──
    graph: dict[str, list[str]] = {k: [] for k in key_to_path}
    for key, path in key_to_path.items():
        for target in _extract_flypig_imports(path):
            # 把 flypig.domain.session 截到最短匹配的模块键
            for module_key in key_to_path:
                if target == module_key or target.startswith(module_key + "."):
                    if module_key != key:  # 不自引用
                        graph[key].append(module_key)

    # ── DFS 找环 ──
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {k: WHITE for k in graph}
    parent: dict[str, str | None] = {k: None for k in graph}

    def dfs(node: str, path: list[str]) -> bool:
        color[node] = GRAY
        path.append(node)
        for neighbor in graph.get(node, []):
            if color.get(neighbor) == GRAY:
                # 找到环
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                violations.append(
                    f"  [CIRCULAR] {' → '.join(cycle)}"
                )
                return True
            elif color.get(neighbor) == WHITE:
                if dfs(neighbor, path):
                    return True
        path.pop()
        color[node] = BLACK
        return False

    for node in list(graph.keys()):
        if color[node] == WHITE:
            dfs(node, [])

    return violations


# ── 低耦合/高内聚 / 数据分离检查器 ──

# 已知合法的硬编码模式（不报错）
ALLOWED_URL_PATTERNS = [
    "api.deepseek.com", "api.openai.com", "api.anthropic.com",
    "api.moonshot.cn", "dashscope.aliyuncs.com", "ark.cn-beijing.volces.com",
    "open.bigmodel.cn", "api-portkey", "portkey",
]

HARDCODE_THRESHOLD_IMPORTS = 25   # 超过此数认为高耦合
HARDCODE_THRESHOLD_PARAMS = 6     # 函数参数超过此数认为设计问题


def check_coupling(file_path: Path) -> list[str]:
    """检查文件耦合度：import 语句过多表示依赖过多"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    import_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("__future__"):
                continue
            import_count += 1

    if import_count > HARDCODE_THRESHOLD_IMPORTS:
        violations.append(
            f"  [COUPLE] {import_count} 条 import（高耦合），超过 {HARDCODE_THRESHOLD_IMPORTS} 条阈值"
        )
    return violations


def check_params(file_path: Path) -> list[str]:
    """检查函数参数数量：参数过多说明职责不单一"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            param_count = len(node.args.args)
            if param_count > HARDCODE_THRESHOLD_PARAMS:
                violations.append(
                    f"  [PARAMS] 函数 {node.name} 有 {param_count} 个参数（> {HARDCODE_THRESHOLD_PARAMS}）"
                )
    return violations


def check_hardcode(file_path: Path) -> list[str]:
    """检查代码中是否硬编码了本应放在配置文件的数据"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    content = file_path.read_text(encoding="utf-8")

    # 1. 检查硬编码的 API Key 密钥模式（sk- / xai- 等已知前缀）
    api_key_pattern = re.compile(r'["\']([sx]k-[a-zA-Z0-9_\-]+)["\']')
    if api_key_pattern.search(content):
        violations.append(
            "  [HARDCODE] 疑似硬编码 API Key（sk-/xai- 前缀），应放在 config.yaml 或环境变量中"
        )

    # 2. 检查硬编码的 HTTP URL（排除含变量格式和已知合法列表）
    url_pattern = re.compile(r'https?://[^\s"\'<>){]+')
    for match in url_pattern.findall(content):
        if "{" in match or "}" in match:
            continue  # f-string 模板 URL，不是硬编码
        if any(pat in match for pat in ALLOWED_URL_PATTERNS):
            continue
        if "localhost" in match or "127.0.0.1" in match:
            continue  # 本地开发地址允许
        violations.append(
            f"  [HARDCODE] 硬编码 URL: {match}，应放在配置文件或 settings 中"
        )
        break  # 一个文件最多报一次

    return violations


# ── 代码质量检查器 ──

MAX_NESTING_DEPTH = 4      # 嵌套深度阈值
MAX_FUNC_LINES = 50        # 函数行数阈值
MAX_FUNC_LINES_WARN = 80   # 函数行数警告线


def _nesting_depth(node: ast.AST, depth: int = 0) -> int:
    """计算 AST 节点的最大嵌套深度"""
    max_d = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While,
                              ast.Try, ast.With, ast.AsyncWith,
                              ast.comprehension)):
            d = _nesting_depth(child, depth + 1)
            if d > max_d:
                max_d = d
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            d = _nesting_depth(child, depth)
            if d > max_d:
                max_d = d
        else:
            d = _nesting_depth(child, depth)
            if d > max_d:
                max_d = d
    return max_d


def check_nesting(file_path: Path) -> list[str]:
    """检查嵌套深度：超过 4 层表明代码复杂度高"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    max_depth = _nesting_depth(tree)
    if max_depth > MAX_NESTING_DEPTH:
        violations.append(
            f"  [NESTING] 最大嵌套深度 {max_depth} 层（> {MAX_NESTING_DEPTH}），建议提前 return 或提取函数"
        )
    return violations


def check_magic_numbers(file_path: Path) -> list[str]:
    """检查魔法数字：不应出现散落的数字字面量"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    content = file_path.read_text(encoding="utf-8")

    # 常见合法数字模式
    LEGAL_PATTERNS = [
        r"self\.\w+\s*=.*\d",        # 类属性赋值
        r"return\s+-?\d",             # 返回常量
        r"raise\s+.*\(\d",            # 异常带状态码
        r"@.*\(\s*\d",                # 装饰器参数
        r"range\(\s*\d",              # range()
        r"max\(\s*\d|min\(\s*\d",     # max/min
        r"sleep\(\s*\d",              # time.sleep
        r"timeout\s*[=:]\s*\d",       # timeout 参数
        r"default\s*[=:]\s*\d",       # 默认值
        r"port\s*[=:]\s*\d",          # 端口号
        r"version\s*[=:]\s*\d",       # 版本号
        r"_MAX_|_MIN_|_LIMIT|_SIZE|_COUNT",  # 命名常量
        r"\.\d{2,4}",                  # 小数（概率/比例）
        r"\{\d\}",                     # 格式化占位符
        r"\b[01]\b",                   # 0 和 1（常见布尔标志）
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            val = node.value
            if val in (0, 1, -1, 100, 1000):
                continue  # 常见通用数字
            # 获取所在行检查是否为合法模式
            line = content.splitlines()[node.lineno - 1] if node.lineno else ""
            # 跳过常量定义（如 MAX_SIZE = 500）
            if re.match(r'^\s*[A-Z_][A-Z0-9_]*\s*=', line):
                continue
            if any(re.search(p, line) for p in LEGAL_PATTERNS):
                continue
            if isinstance(val, (int, float)) and abs(val) >= 2:
                violations.append(
                    f"  [MAGIC] 第 {node.lineno} 行：魔法数字 {val}，建议定义为命名常量"
                )
                break  # 一个文件最多报一次

    return violations


def check_empty_except(file_path: Path) -> list[str]:
    """检查空 except: pass（静默吞异常）"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                # except: - 裸 except
                violations.append(
                    f"  [EMPTY_EXC] 第 {node.lineno} 行：裸 except:，应指定异常类型"
                )
                break
            if (node.type is not None
                    and len(node.body) == 1
                    and isinstance(node.body[0], ast.Pass)):
                violations.append(
                    f"  [EMPTY_EXC] 第 {node.lineno} 行：except {ast.dump(node.type)}: pass，静默吞异常"
                )
                break
    return violations


def check_long_function(file_path: Path) -> list[str]:
    """检查函数体行数：超过 50 行应考虑拆分"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    content = file_path.read_text(encoding="utf-8").splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.body:
                continue
            first_line = node.lineno
            last_line = max(
                (n.lineno for n in ast.walk(node) if hasattr(n, 'lineno')),
                default=first_line
            )
            func_lines = last_line - first_line + 1
            if func_lines > MAX_FUNC_LINES_WARN:
                violations.append(
                    f"  [LONG_FUNC] {node.name} {func_lines} 行（> {MAX_FUNC_LINES_WARN}），建议拆分"
                )
                break
            elif func_lines > MAX_FUNC_LINES:
                violations.append(
                    f"  [LONG_FUNC] {node.name} {func_lines} 行（> {MAX_FUNC_LINES}），考虑拆分"
                )
    return violations


def check_todo_left(file_path: Path) -> list[str]:
    """非骨架文件中不可遗留 TODO/FIXME（应在骨架中标记 TODO）"""
    violations: list[str] = []
    content = file_path.read_text(encoding="utf-8")
    stripped = content.strip()
    if not stripped:
        return violations

    # 检查是否骨架文件（只有 docstring 内容）
    tree = read_tree(file_path)
    if tree is None:
        return violations
    docstring = ast.get_docstring(tree)
    has_real_code = False
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef,
                              ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign)):
            has_real_code = True
            break

    if not has_real_code:
        return violations  # 骨架文件允许 TODO

    # 非骨架文件检查 TODO/FIXME
    for i, line in enumerate(content.splitlines(), 1):
        stripped_line = line.strip()
        if stripped_line.startswith("#") and "TODO" in stripped_line:
            violations.append(f"  [TODO] 第 {i} 行：{stripped_line}")
            break  # 一个文件最多报一次

    return violations


def check_print(file_path: Path) -> list[str]:
    """检查生产代码中不应有 print()（应使用 loguru 日志）"""
    violations: list[str] = []
    if "test_" in file_path.name or file_path.parent.name == "tests":
        return violations  # 测试代码允许 print
    if file_path.name == "__init__.py":
        return violations

    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == "print":
                violations.append(
                    f"  [PRINT] 第 {node.lineno} 行：print()，应使用 logger.info() 或 logger.debug()"
                )
                break
    return violations


def check_assert(file_path: Path) -> list[str]:
    """检查生产代码中不应有 assert（应使用显式判断 + 异常）"""
    violations: list[str] = []
    if "test_" in file_path.name or file_path.parent.name == "tests":
        return violations  # 测试代码允许 assert
    if file_path.name == "__init__.py":
        return violations

    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            violations.append(
                f"  [ASSERT] 第 {node.lineno} 行：assert，应使用 if + 异常处理"
            )
            break
    return violations


def check_magic_strings(file_path: Path) -> list[str]:
    """检查魔法字符串：重复出现 3+ 次的字符串字面量应定义为常量"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    # 收集所有字符串字面量
    strings: dict[str, list[int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            # 跳过太短/太长的字符串
            if len(s) < 3 or len(s) > 50:
                continue
            # 跳过常见的无害字符串
            if s in ("", " ", "__main__", "__name__", "__file__", "utf-8",
                      "r", "w", "a", "rb", "wb", "strict",
                      "json", "text", "html", "xml", "yaml",
                      "True", "False", "None", "self", "cls"):
                continue
            # 跳过看起来像路径/URL 的字符串
            if s.startswith(("./", "/", "http", "https", "{", "data:")):
                continue
            # 跳过 f-string 模板
            if "{" in s or "}" in s:
                continue
            # 跳过 import 语句中的模块名（在 ast 中会被解析）
            strings.setdefault(s, []).append(node.lineno)

    # 报告重复 3+ 次且不是 import 路径的字符串
    for s, lines in strings.items():
        # 跳过单字母/数字字符串
        if len(set(s)) <= 2:
            continue
        # 跳过看起来像字典 key 的简单的词（大概率是合法的配置 key）
        if len(lines) >= 3 and not s.startswith("_"):
            violations.append(
                f"  [MSTR] 字符串 \"{s}\" 出现了 {len(lines)} 次（行 {lines[0]}, {lines[1]}...），建议定义为常量"
            )
            break  # 一个文件最多报一次

    return violations


def check_many_returns(file_path: Path) -> list[str]:
    """检查函数返回点过多（>4）"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            returns = sum(1 for _ in ast.walk(node) if isinstance(_, ast.Return))
            if returns > 4:
                violations.append(
                    f"  [RETURNS] {node.name} 有 {returns} 个 return 语句（> 4），流程过于复杂"
                )
                break
    return violations


def check_large_class(file_path: Path) -> list[str]:
    """检查类是否过大：方法 > 15 或 __init__ 属性 > 10"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = sum(1 for _ in ast.walk(node)
                          if isinstance(_, (ast.FunctionDef, ast.AsyncFunctionDef))
                          and not _.name.startswith("_"))
            if methods > 15:
                violations.append(
                    f"  [CLASS] {node.name} 有 {methods} 个公开方法（> 15），建议拆分"
                )
                break
            # 检查 __init__ 中 self.xxx 赋值数量
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
                    attrs = sum(1 for _ in ast.walk(item)
                                if isinstance(_, ast.Attribute)
                                and isinstance(_.value, ast.Name)
                                and _.value.id == "self"
                                and isinstance(_.ctx, ast.Store))
                    if attrs > 10:
                        violations.append(
                            f"  [CLASS] {node.name}.__init__ 赋值 {attrs} 个属性（> 10），职责过多"
                        )
                        break
    return violations


def check_abc_without_abstract(file_path: Path) -> list[str]:
    """检查继承 ABC 的类是否至少有一个 @abstractmethod"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            is_abc = any(
                isinstance(b, ast.Name) and b.id == "ABC"
                for b in node.bases
            )
            if not is_abc:
                continue
            has_abstract = False
            for item in ast.walk(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for deco in item.decorator_list:
                        if isinstance(deco, ast.Name) and deco.id == "abstractmethod":
                            has_abstract = True
                            break
                    if has_abstract:
                        break
            if not has_abstract:
                violations.append(
                    f"  [ABC] {node.name} 继承 ABC 但无 @abstractmethod，应改为普通类"
                )
                break
    return violations


REQUIRED_DOC_SECTIONS = ["为什么做", "实现方法", "层&依赖"]
"""实代码文件必须在 docstring 中包含的 FlyPig 格式段落"""


def _is_skeleton_file(file_path: Path) -> bool:
    """判断是否骨架文件（只有 docstring + 类骨架，没有实代码）"""
    tree = read_tree(file_path)
    if tree is None:
        return True
    docstring = ast.get_docstring(tree)
    has_real_code = False
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef,
                              ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign)):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            has_real_code = True
            break
    return not has_real_code


def check_docstring_quality(file_path: Path) -> list[str]:
    """检查 docstring 质量：
    - 符合 FlyPig docstring 格式：为什么做 / 实现方法 / 层&依赖
    - domain 层的文件必须在 docstring 中标注 DDD 类型（值对象/实体/聚合根等）
    - docstring 不应是单行敷衍"""
    violations: list[str] = []
    content = file_path.read_text(encoding="utf-8")
    stripped = content.strip()
    if not stripped:
        return violations

    tree = read_tree(file_path)
    if tree is None:
        return violations

    docstring = ast.get_docstring(tree)
    if not docstring:
        return violations  # 已有 DOC 检查

    # ── 0. 骨架文件跳过检查 ──
    if _is_skeleton_file(file_path):
        return violations

    # ── 1. 检查 docstring 不是单行敷衍 ──
    lines = docstring.strip().split("\n")
    if len(lines) == 1 and len(docstring) < 20:
        violations.append(
            "  [DOCQ] docstring 太短，应包含：为什么做 / 实现方法 / 层&依赖"
        )
        return violations

    # ── 2. 检查 FlyPig docstring 必填段落 ──
    missing = [s for s in REQUIRED_DOC_SECTIONS if s not in docstring]
    if missing:
        violations.append(
            f"  [DOCQ] 缺少段落：{' / '.join(missing)}"
        )

    # ── 3. domain 层必须标注 DDD 类型 ──
    source_layer = None
    for skip in ("interfaces", "event", "specification", "prompts"):
        if skip in file_path.parts:
            break
    else:
        try:
            rel = file_path.relative_to(Path(__file__).resolve().parent.parent / "flypig")
            if len(rel.parts) >= 2:
                source_layer = rel.parts[1]
        except ValueError:
            pass

    if source_layer == "domain" and file_path.name != "__init__.py":
        ddd_keywords = ["值对象", "实体", "聚合根", "领域事件", "域服务", "规格", "工厂"]
        if not any(kw in docstring for kw in ddd_keywords):
            violations.append(
                "  [DOCQ] domain 层文件应标注 DDD 类型（值对象/实体/聚合根等）"
            )

    return violations


# ══════════════════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════════════════

def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent / "flypig"
    if not base_dir.exists():
        print(f"[FAIL] 未找到 flypig 目录：{base_dir}")
        return 1

    # 注册所有检查器
    checks: list[tuple[str, str, callable]] = [
        ("layer",    "层依赖方向",         check_layer),
        ("ddd",      "DDD 基类继承",       check_ddd_inheritance),
        ("wild",     "通配导入",           check_wildcard),
        ("doc",      "文件级 docstring",   check_docstring),
        ("all",      "__init__.__all__",   check_all_export),
        ("exc",      "裸异常抛出",         check_bare_exception),
        ("size",     "文件行数超限",       check_file_size),
        ("skel",     "骨架文件标记",       check_skeleton_marker),
        ("couple",   "高耦合(import过多)", check_coupling),
        ("params",   "参数过多",           check_params),
        ("hardcode", "硬编码数据",         check_hardcode),
        ("nesting",  "嵌套过深",           check_nesting),
        ("magic",    "魔法数字",           check_magic_numbers),
        ("empty_exc","空异常捕获",         check_empty_except),
        ("longfunc", "函数过长",           check_long_function),
        ("todo",     "遗留 TODO",          check_todo_left),
        ("print",    "生产代码print",       check_print),
        ("assert",   "生产代码assert",      check_assert),
        ("mstr",     "魔法字符串",          check_magic_strings),
        ("returns",  "返回点过多",          check_many_returns),
        ("class",    "类过大/属性过多",     check_large_class),
        ("abc",      "ABC无抽象方法",       check_abc_without_abstract),
        ("docq",     "docstring质量",       check_docstring_quality),
    ]

    results: dict[str, list[str]] = {key: [] for key, _, _ in checks}
    results["circular"] = []

    py_files = sorted(base_dir.rglob("*.py"))

    for file_path in py_files:
        if any(skip in file_path.parts for skip in SKIP_DIRS):
            continue
        if "__pycache__" in file_path.parts:
            continue

        rel = file_path.relative_to(base_dir.parent)

        for key, _, check_fn in checks:
            if key == "ddd":
                source_layer = get_layer(file_path, base_dir.parent)
                if source_layer != "domain":
                    continue

            vio = check_fn(file_path, base_dir.parent) if key == "layer" else check_fn(file_path)
            if vio is None:
                vio = []
            for v in vio:
                results[key].append(f"  {rel}:{v}")

    # ── 循环依赖检测（独立运行，非逐文件） ──
    filted_files = [
        f for f in py_files
        if not any(skip in f.parts for skip in SKIP_DIRS)
        and "__pycache__" not in f.parts
    ]
    results["circular"] = check_circular(filted_files, base_dir.parent)

    # ── 输出 ──
    total = sum(len(v) for v in results.values())
    has_error = total > 0

    print("=" * 60)
    print("  FlyPig 架构合规检查报告")
    print("=" * 60)

    if not has_error:
        print("\n[PASS] 全部通过！架构合规。")
        return 0

    labels = {
        "layer":    ("LAYER",    "层依赖方向"),
        "ddd":      ("DDD",      "DDD 基类继承"),
        "wild":     ("WILD",     "通配导入"),
        "doc":      ("DOC",      "文件级 docstring"),
        "all":      ("ALL",      "__init__.__all__"),
        "exc":      ("EXC",      "裸异常抛出"),
        "size":     ("SIZE",     "文件行数超限"),
        "skel":     ("SKEL",     "骨架文件标记"),
        "couple":   ("COUPLE",   "高耦合(import过多)"),
        "params":   ("PARAMS",   "函数参数过多"),
        "hardcode": ("HARDCODE", "硬编码数据"),
        "nesting":  ("NESTING",  "嵌套过深"),
        "magic":    ("MAGIC",    "魔法数字"),
        "empty_exc":("EMPTY_EXC","空异常捕获"),
        "longfunc": ("LONG_FUNC","函数过长"),
        "todo":     ("TODO",     "遗留 TODO"),
        "print":    ("PRINT",    "生产代码print"),
        "assert":   ("ASSERT",   "生产代码assert"),
        "mstr":     ("MSTR",     "魔法字符串"),
        "returns":  ("RETURNS",  "返回点过多"),
        "class":    ("CLASS",    "类过大/属性过多"),
        "abc":      ("ABC",      "ABC无抽象方法"),
        "docq":     ("DOCQ",     "docstring质量"),
        "circular": ("CIRCULAR", "循环依赖"),
    }

    for key, violations in results.items():
        if not violations:
            continue
        kind, title = labels.get(key, (key.upper(), key))
        print(f"\n[FAIL] {title}（{len(violations)} 处）")
        print("\n".join(violations))

    print(f"\n{'=' * 60}")
    print(f"  共 {total} 处违规")
    print(f"  请修复后再提交")
    print(f"{'=' * 60}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
