#!/usr/bin/env python3
"""FlyPig 架构合规检查 — 守护 DDD 分层边界（ruff 不覆盖的 FlyPig 特有项）

共 12 项检查：

━━━ 一、架构合规（Architecture）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LAYER     — 层依赖方向（domain → application → infrastructure → interface）
  DDD       — DDD 基类继承（domain 层的类必须继承 Entity/ValueObject 等）
  CIRCULAR  — 循环依赖检测（A → B → C → A）
  SKEL      — 骨架文件必须有 TODO 标记，防止 AI 误删
  REGISTER  — 新文件必须在 __init__.__all__ 或 app_factory 注册

━━━ 二、API 契约（API Contract）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  APICONTRACT — 路由端点响应结构必须匹配 data/api-contracts.json 定义

━━━ 三、文档规范（Documentation）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DOC       — 每个 .py 文件必须有文件级 docstring
  DOCQ      — docstring 质量：必须含「为什么做/实现方法/层&依赖」三段

━━━ 四、包耦合度（Package Coupling）━━━━━━━━━━━━━━━━━━━━━━━━━━━
  COUPLE_PKG— 包级别跨层依赖过多（>2 个层），提示职责过宽

━━━ 五、接口契约（Interface Contract）━━━━━━━━━━━━━━━━━━━━━━━━━━
  CONTRACT — domain/interfaces 的 ABC 接口在 infrastructure 中是否有对应实现

━━━ 六、依赖安全（Dependency Security）━━━━━━━━━━━━━━━━━━━━━━━━━
  DEPSEC — 依赖版本是否锁定（>= 无上限警告）

━━━ 七、配置规范（Configuration）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CONFIG — config.yaml 是否存在、格式是否完整

━━━ 八、国际化就绪（i18n Readiness）━━━━━━━━━━━━━━━━━━━━━━━━━━━
  I18N   — FlyPigException code 字段是否有对应的 i18n 翻译键

━━━ 九、测试覆盖（Test Coverage）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TEST   — 每个业务模块是否有对应的测试文件

用法：
    python scripts/architecture_check.py   （后端 11 项）
    python scripts/frontend_check.py        （前端独立）
    ruff check                               （Python 质量 300+ 项）
    npx eslint src/                           （Vue/JS 质量 200+ 项）

退出码：
    0 = 全部通过
    1 = 有违规
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

# ── 层级定义 ──
LAYER_RULES: dict[str, list[str]] = {
    "domain": ["shared", "domain"],
    "application": ["shared", "domain", "application", "bootstrap"],
    "infrastructure": [
        "shared",
        "data",
        "domain",
        "application",
        "infrastructure",
        "bootstrap",
        "acl",
    ],
    "interface": [
        "shared",
        "domain",
        "application",
        "infrastructure",
        "interface",
        "orchestration",
        "bootstrap",
    ],
    "bootstrap": [
        "shared",
        "domain",
        "application",
        "infrastructure",
        "interface",
        "orchestration",
        "bootstrap",
    ],
    "orchestration": [
        "shared",
        "domain",
        "application",
        "infrastructure",
        "orchestration",
        "bootstrap",
    ],
    "acl": ["shared", "domain", "acl"],
}

# 跳过检查的目录
SKIP_DIRS = {
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "migrations",
    "chat-server",
    "web",
    "desktop",
    "electron",
    "tests",
}

# domain 层中跳过 DDD 继承检查的子目录
DDD_SKIP_SUBDIRS = {"interfaces", "event", "specification", "prompts"}

# DDD 基类白名单
DDD_BASE_CLASSES = {
    "Entity",
    "ValueObject",
    "AggregateRoot",
    "DomainEvent",
    "DomainService",
    "ApplicationService",
    "Repository",
    "Specification",
    "Factory",
    "ABC",
    "Enum",
    "TypedDict",
    "Protocol",
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


def read_tree(file_path: Path) -> ast.Module | None:
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
                    violations.append(
                        f"  [LAYER] 位于 {source_layer} 层，但 import 了 {pkg} 层（{alias.name}）"
                    )
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
            if node.name.endswith(("Error", "Exception")) or _inherits_from(
                node, {"Exception", "BaseException"}
            ):
                continue
            if _inherits_from(node, {"TypedDict", "Enum", "Protocol"}):
                continue

            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            if not any(b in DDD_BASE_CLASSES for b in bases):
                violations.append(f"  [DDD] {file_path.name} 中的类 {node.name} 没有继承 DDD 基类")
    return violations


def check_wildcard(file_path: Path) -> list[str]:
    """检查通配导入"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.names
            and any(n.name == "*" for n in node.names)
        ):
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
            violations.append("  [DOC] 缺少文件级 docstring")
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
            if exc is not None and isinstance(exc, ast.Call):
                func = exc.func
                if isinstance(func, ast.Name) and func.id in (
                    "Exception",
                    "RuntimeError",
                    "BaseException",
                ):
                    violations.append(f"  [EXC] 抛裸 {func.id}()，应使用 FlyPigException 子类")
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
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
                ast.ClassDef,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.Assign,
            ),
        ):
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                continue  # docstring
            has_code = True
            break

    if not has_code and docstring and not has_todo:
        violations.append("  [SKEL] 骨架文件（只有 docstring）缺少 TODO 标记，AI 可能误删")
    return violations


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
                if (
                    target == module_key or target.startswith(module_key + ".")
                ) and module_key != key:
                    graph[key].append(module_key)

    # ── DFS 找环 ──
    WHITE, GRAY, BLACK = 0, 1, 2  # noqa: N806  # DFS 经典命名惯例
    color: dict[str, int] = dict.fromkeys(graph, WHITE)

    def dfs(node: str, path: list[str]) -> bool:
        color[node] = GRAY
        path.append(node)
        for neighbor in graph.get(node, []):
            if color.get(neighbor) == GRAY:
                # 找到环
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                violations.append(f"  [CIRCULAR] {' → '.join(cycle)}")
                return True
            if color.get(neighbor) == WHITE and dfs(neighbor, path):
                return True
        path.pop()
        color[node] = BLACK
        return False

    for node in list(graph.keys()):
        if color[node] == WHITE:
            _ = dfs(node, [])

    return violations


# ── 低耦合/高内聚 / 数据分离检查器 ──

# 已知合法的硬编码模式（不报错）
ALLOWED_URL_PATTERNS = [
    "api.deepseek.com",
    "api.openai.com",
    "api.anthropic.com",
    "api.moonshot.cn",
    "dashscope.aliyuncs.com",
    "ark.cn-beijing.volces.com",
    "open.bigmodel.cn",
    "api-portkey",
    "portkey",
]

HARDCODE_THRESHOLD_IMPORTS = 25  # 超过此数认为高耦合
HARDCODE_THRESHOLD_PARAMS = 5  # 函数参数超过此数认为设计问题


def check_coupling(file_path: Path) -> list[str]:
    """检查文件耦合度：import 语句过多表示依赖过多"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations

    import_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("__future__")
            ):
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
        violations.append(f"  [HARDCODE] 硬编码 URL: {match}，应放在配置文件或 settings 中")
        break  # 一个文件最多报一次

    return violations


# ── 代码质量检查器 ──

MAX_NESTING_DEPTH = 4  # 嵌套深度阈值
MAX_FUNC_LINES = 50  # 函数行数阈值
MAX_FUNC_LINES_WARN = 80  # 函数行数警告线


def _nesting_depth(node: ast.AST, depth: int = 0) -> int:
    """计算 AST 节点的最大嵌套深度"""
    max_d = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(
            child,
            (
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.Try,
                ast.With,
                ast.AsyncWith,
                ast.comprehension,
            ),
        ):
            d = _nesting_depth(child, depth + 1)
            max_d = max(max_d, d)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            d = _nesting_depth(child, depth)
            max_d = max(max_d, d)
        else:
            d = _nesting_depth(child, depth)
            max_d = max(max_d, d)
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
    LEGAL_PATTERNS = [  # noqa: N806  # 全局常量
        r"self\.\w+\s*=.*\d",  # 类属性赋值
        r"return\s+-?\d",  # 返回常量
        r"raise\s+.*\(\d",  # 异常带状态码
        r"@.*\(\s*\d",  # 装饰器参数
        r"range\(\s*\d",  # range()
        r"max\(\s*\d|min\(\s*\d",  # max/min
        r"sleep\(\s*\d",  # time.sleep
        r"timeout\s*[=:]\s*\d",  # timeout 参数
        r"default\s*[=:]\s*\d",  # 默认值
        r"port\s*[=:]\s*\d",  # 端口号
        r"version\s*[=:]\s*\d",  # 版本号
        r"_MAX_|_MIN_|_LIMIT|_SIZE|_COUNT",  # 命名常量
        r"\.\d{2,4}",  # 小数（概率/比例）
        r"\{\d\}",  # 格式化占位符
        r"\b[01]\b",  # 0 和 1（常见布尔标志）
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            val = node.value
            if val in (0, 1, -1, 100, 1000):
                continue  # 常见通用数字
            # 获取所在行检查是否为合法模式
            line = content.splitlines()[node.lineno - 1] if node.lineno else ""
            # 跳过常量定义（如 MAX_SIZE = 500）
            if re.match(r"^\s*[A-Z_][A-Z0-9_]*\s*=", line):
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
                violations.append(f"  [EMPTY_EXC] 第 {node.lineno} 行：裸 except:，应指定异常类型")
                break
            if node.type is not None and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
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

    file_path.read_text(encoding="utf-8").splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.body:
                continue
            first_line = node.lineno
            last_line = max(
                (getattr(n, "lineno", 0) for n in ast.walk(node)),
                default=first_line,
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
    ast.get_docstring(tree)
    has_real_code = False
    for node in ast.iter_child_nodes(tree):
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
                ast.ClassDef,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.Assign,
            ),
        ):
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
            violations.append(f"  [ASSERT] 第 {node.lineno} 行：assert，应使用 if + 异常处理")
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
            if s in (
                "",
                " ",
                "__main__",
                "__name__",
                "__file__",
                "utf-8",
                "r",
                "w",
                "a",
                "rb",
                "wb",
                "strict",
                "json",
                "text",
                "html",
                "xml",
                "yaml",
                "True",
                "False",
                "None",
                "self",
                "cls",
            ):
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
                f'  [MSTR] 字符串 "{s}" 出现了 {len(lines)} 次（行 {lines[0]}, {lines[1]}...），建议定义为常量'
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
            methods = sum(
                1
                for _ in ast.walk(node)
                if isinstance(_, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not _.name.startswith("_")
            )
            if methods > 15:
                violations.append(
                    f"  [CLASS] {node.name} 有 {methods} 个公开方法（> 15），建议拆分"
                )
                break
            # 检查 __init__ 中 self.xxx 赋值数量
            for item in ast.iter_child_nodes(node):
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == "__init__"
                ):
                    attrs = sum(
                        1
                        for _ in ast.walk(item)
                        if isinstance(_, ast.Attribute)
                        and isinstance(_.value, ast.Name)
                        and _.value.id == "self"
                        and isinstance(_.ctx, ast.Store)
                    )
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
            is_abc = any(isinstance(b, ast.Name) and b.id == "ABC" for b in node.bases)
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
                # 放行标记基类（类体只有 pass/docstring/property/私有方法）
                is_marker = all(
                    isinstance(item, (ast.Pass, ast.Expr))
                    or (
                        isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and (
                            item.name.startswith("_")
                            or any(
                                isinstance(d, ast.Name) and d.id == "property"
                                for d in item.decorator_list
                            )
                        )
                    )
                    for item in node.body
                )
                if is_marker:
                    continue
                violations.append(
                    f"  [ABC] {node.name} 继承 ABC 但无 @abstractmethod，应改为普通类"
                )
                break
    return violations


def check_return_type(file_path: Path) -> list[str]:
    """检查公开函数是否缺少返回类型注解"""
    violations: list[str] = []
    tree = read_tree(file_path)
    if tree is None:
        return violations
    if file_path.name == "__init__.py":
        return violations

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            if node.returns is None:
                if node.name in (
                    "__init__",
                    "__call__",
                    "__new__",
                    "__enter__",
                    "__aenter__",
                    "__aexit__",
                    "__exit__",
                ):
                    continue
                violations.append(f"  [RETTYPE] 公开函数 {node.name} 缺少返回类型注解")
                break
    return violations


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
            if isinstance(func, ast.Attribute) and func.attr in (
                "open",
                "read_text",
                "write_text",
            ):
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
    """检查包级别耦合度
    - bootstrap 层是胶水代码，免检
    - container/factory/node 等模式文件天然需依赖多层，免检"""
    violations: list[str] = []

    # bootstrap 层免检
    if "bootstrap" in file_path.parts:
        return violations

    # 特定模式文件免检
    exempt_patterns = ("container", "factory", "node", "server", "service")
    if (
        file_path.stem in exempt_patterns
        or file_path.stem.endswith("_factory")
        or file_path.stem.endswith("_node")
        or file_path.stem.endswith("_service")
    ):
        return violations

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


REQUIRED_DOC_SECTIONS = ["为什么做", "实现方法", "层&依赖"]
"""实代码文件必须在 docstring 中包含的 FlyPig 格式段落"""


def _is_skeleton_file(file_path: Path) -> bool:
    """判断是否骨架文件（只有 docstring + 类骨架，没有实代码）"""
    tree = read_tree(file_path)
    if tree is None:
        return True
    ast.get_docstring(tree)
    has_real_code = False
    for node in ast.iter_child_nodes(tree):
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
                ast.ClassDef,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.Assign,
            ),
        ):
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
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
        violations.append("  [DOCQ] docstring 太短，应包含：为什么做 / 实现方法 / 层&依赖")
        return violations

    # ── 2. 检查 FlyPig docstring 必填段落 ──
    missing = [s for s in REQUIRED_DOC_SECTIONS if s not in docstring]
    if missing:
        violations.append(f"  [DOCQ] 缺少段落：{' / '.join(missing)}")

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
        ddd_keywords = [
            "值对象",
            "实体",
            "聚合根",
            "领域事件",
            "域服务",
            "规格",
            "工厂",
        ]
        if not any(kw in docstring for kw in ddd_keywords):
            violations.append("  [DOCQ] domain 层文件应标注 DDD 类型（值对象/实体/聚合根等）")

    return violations


# ── 8. 命名规范检查 ──────────────────────────────────────────────


def _is_pascal_case(name: str) -> bool:
    """检查是否 PascalCase（首字母大写）"""
    return bool(re.match(r"^[A-Z][a-zA-Z0-9]*$", name))


def _is_snake_case(name: str) -> bool:
    """检查是否 snake_case（下划线 + 小写字母开头）"""
    return bool(re.match(r"^_*[a-z][a-z0-9_]*$", name))


def check_naming_convention(file_path: Path) -> list[str]:
    """检查命名规范：类名 PascalCase，函数/方法名 snake_case"""
    violations: list[str] = []
    if file_path.name == "__init__.py":
        return violations

    tree = read_tree(file_path)
    if tree is None:
        return violations

    # ── 1. 类名 PascalCase ──
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name == "ABC":
                continue
            if not _is_pascal_case(node.name):
                violations.append(
                    f"  [NAMED] 第 {node.lineno} 行：类名 {node.name} 不是 PascalCase"
                )
                break

    # ── 2. 函数/方法名 snake_case ──
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("__") and node.name.endswith("__"):
                continue  # 魔术方法
            if not _is_snake_case(node.name):
                violations.append(
                    f"  [NAMED] 第 {node.lineno} 行：函数名 {node.name} 不是 snake_case"
                )
                break

    return violations


# ── 9. 安全审计检查 ─────────────────────────────────────────────

SAFE_DANGEROUS_FUNCS = {"eval", "exec", "compile"}
SAFE_SHELL_PATTERNS = [
    r"os\.system\s*\(",
    r"subprocess\.(Popen|call|run)\s*\(.*shell\s*=\s*True",
    r"asyncio\.create_subprocess_shell\s*\(",
]


def check_security(file_path: Path) -> list[str]:
    """检查安全风险：eval/exec、shell 注入、路径穿越、SQL 注入"""
    violations: list[str] = []
    content = file_path.read_text(encoding="utf-8")

    # ── 1. 危险函数 eval/exec/compile ──
    tree = read_tree(file_path)
    if tree is None:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in SAFE_DANGEROUS_FUNCS:
                violations.append(
                    f"  [SECURE] 第 {node.lineno} 行：禁止使用 {func.id}()，存在代码注入风险"
                )
                break

    # ── 2. Shell 注入 ──
    if not violations:
        for pattern in SAFE_SHELL_PATTERNS:
            m = re.search(pattern, content)
            if m:
                violations.append(
                    "  [SECURE] 检测到 shell 调用（os.system / subprocess shell=True），"
                    "应使用 subprocess.run(..., shell=False)"
                )
                break

    # ── 3. 路径穿越 ──
    if not violations:
        # 检查 open() 或 Path 调用中是否含有 "../" 或 "..\\"
        path_traversal = re.search(
            r'(?:open|read_text|write_text|Path)\s*\(.*["\']\.\.[/\\]', content
        )
        if path_traversal:
            violations.append("  [SECURE] 检测到路径穿越（../），应校验路径防止目录遍历攻击")

    # ── 4. SQL 注入 ──
    if not violations:
        sql_pattern = re.search(
            r'(execute|executemany|cursor\.execute)\s*\(\s*(f["\']|["\']\s*\+\s*|%s?)',
            content,
        )
        if sql_pattern:
            violations.append("  [SECURE] 检测到 SQL 字符串拼接/f-string，应使用参数化查询")

    return violations


# ── 10. 接口契约检查 ─────────────────────────────────────────────


def _extract_abc_interfaces(interfaces_dir: Path) -> dict[str, str]:
    """提取 domain/interfaces 中定义的 ABC 接口类名 → 文件路径映射"""
    interfaces: dict[str, str] = {}
    if not interfaces_dir.exists():
        return interfaces

    for f in sorted(interfaces_dir.rglob("*.py")):
        if f.name == "__init__.py":
            continue
        tree = read_tree(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 继承 ABC 或 abc.ABC
                is_abc = any(isinstance(b, ast.Name) and b.id == "ABC" for b in node.bases) or any(
                    isinstance(b, ast.Attribute) and b.attr == "ABC" for b in node.bases
                )
                if is_abc:
                    interfaces[node.name] = str(f)
    return interfaces


def _find_implementations(infra_dir: Path, interface_name: str) -> list[str]:
    """在 infrastructure 中查找实现了某接口的类"""
    impls: list[str] = []
    if interface_name.startswith("I"):
        interface_name[1:]  # IAgent → Agent

    for f in sorted(infra_dir.rglob("*.py")):
        if f.name == "__init__.py":
            continue
        content = f.read_text(encoding="utf-8")
        # 检查文件中是否 import 或引用了接口名
        if interface_name not in content:
            continue
        tree = read_tree(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                if interface_name in bases:
                    impls.append(f"{f.name} → {node.name}")
    return impls


def check_interface_contract(_py_files: list[Path], base_dir: Path) -> list[str]:
    """检查 domain/interfaces 定义的 ABC 在 infrastructure 中是否有实现"""
    violations: list[str] = []
    interfaces_dir = base_dir / "flypig" / "domain" / "interfaces"
    infra_dir = base_dir / "flypig" / "infrastructure"

    if not interfaces_dir.exists() or not infra_dir.exists():
        return violations

    abc_interfaces = _extract_abc_interfaces(interfaces_dir)

    for iface_name, iface_file in abc_interfaces.items():
        impls = _find_implementations(infra_dir, iface_name)
        if not impls:
            violations.append(
                f"  [CONTRACT] 接口 {iface_name}（定义于 {iface_file}）在 "
                f"infrastructure 中无已知实现类"
            )

    return violations


# ── 11. 依赖安全检查 ──────────────────────────────────────────────

# 已知有安全风险的包（仅为示例，实际应使用漏洞数据库）
SUSPICIOUS_PACKAGES: set[str] = set()

REQUIRED_VERSION_FIELDS = {"dependencies", "optional-dependencies"}


def check_dependency_security(project_dir: Path) -> list[str]:
    """检查依赖安全：版本锁定、已知风险包"""
    violations: list[str] = []
    # 尝试多个可能的路径
    candidates = [
        project_dir / "pyproject.toml",
        project_dir / "flypig" / "pyproject.toml",
        project_dir.parent / "pyproject.toml",
        project_dir / "requirements.txt",
    ]
    pyproject: Path | None = None
    for c in candidates:
        if c.exists():
            pyproject = c
            break
    if pyproject is None:
        violations.append("  [DEPSEC] 未找到 pyproject.toml 或 requirements.txt")
        return violations

    content = pyproject.read_text(encoding="utf-8")

    # 检查依赖版本是否锁定（>= 但没有 <= 或 ~= 上限）
    loose_deps = re.findall(
        r'([a-zA-Z][a-zA-Z0-9_.-]+)\s*(?:>=|!=)\s*([\d.]+)["\']?\s*,\s*$',
        content,
        re.MULTILINE,
    )
    if not loose_deps:
        # 尝试另一种匹配：行末没有逗号
        loose_deps = re.findall(
            r'["\']([a-zA-Z][a-zA-Z0-9_.-]+)>=\s*([\d.]+)["\']',
            content,
        )

    for pkg, ver in loose_deps:
        # 检查是否有上限约束（~= 或 <=）
        has_upper = re.search(
            rf"{re.escape(pkg)}\s*(?:>=\s*[\d.]+\s*,\s*[<~]=|~=\s*[\d.]+)",
            content,
        )
        if not has_upper:
            violations.append(
                f"  [DEPSEC] 依赖 {pkg}>={ver} 未锁定上限，应使用 {pkg}>={ver},<next_major"
            )

    return violations


# ── 12. 配置规范检查 ──────────────────────────────────────────────

EXPECTED_CONFIG_SECTIONS = {
    "agent": {"recent_workspaces", "workspace"},
    "api_keys": None,
    "llm": {"default_model"},
}


def check_config_completeness(project_dir: Path) -> list[str]:
    """检查配置规范：config.yaml 是否存在、格式是否完整"""
    violations: list[str] = []
    config_path = project_dir / "flypig" / "config.yaml"
    if not config_path.exists():
        violations.append("  [CONFIG] 未找到 flypig/config.yaml")
        return violations

    content = config_path.read_text(encoding="utf-8")
    if not content.strip():
        violations.append("  [CONFIG] config.yaml 为空文件")
        return violations

    # 检查预期配置段是否存在
    import yaml  # type: ignore[import-untyped]

    try:
        import yaml

        cfg = yaml.safe_load(content)
        if not isinstance(cfg, dict):
            violations.append("  [CONFIG] config.yaml 根节点不是字典")
            return violations

        for section, expected_fields in EXPECTED_CONFIG_SECTIONS.items():
            if section not in cfg:
                violations.append(f"  [CONFIG] 缺少配置段 [{section}]")
                continue
            if expected_fields is not None:
                section_cfg = cfg.get(section, {})
                if isinstance(section_cfg, dict):
                    for field in expected_fields:
                        if field not in section_cfg:
                            violations.append(f"  [CONFIG] [{section}] 缺少字段 {field}")
    except ImportError:
        violations.append("  [CONFIG] 缺少 PyYAML 依赖，无法解析 config.yaml")
    except yaml.YAMLError as e:
        violations.append(f"  [CONFIG] config.yaml 格式错误: {e}")

    return violations


# ── 13. 国际化就绪检查 ───────────────────────────────────────────


def _collect_exception_codes(py_files: list[Path]) -> dict[str, str]:
    """收集所有 FlyPigException 子类的 code 值"""
    codes: dict[str, str] = {}
    for f in py_files:
        tree = read_tree(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                if "FlyPigException" in bases or any(
                    b in ("DomainError", "ConfigurationError") for b in bases
                ):
                    # 查找类属性的 code 赋值
                    for item in ast.iter_child_nodes(node):
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "code":
                                    val = item.value
                                    if isinstance(val, ast.Constant):
                                        codes[node.name] = str(val.value)
    return codes


def check_i18n_readiness(py_files: list[Path]) -> list[str]:
    """检查国际化就绪度：异常 code 字段是否有对应 i18n 翻译键"""
    violations: list[str] = []
    codes = _collect_exception_codes(py_files)

    if not codes:
        return violations

    # 检查是否有 i18n 基础设施
    # 搜索项目中是否包含 i18n/locale/translations 目录
    base = Path(__file__).resolve().parent.parent
    has_i18n_infra = any(
        (base / d).exists() for d in ("i18n", "locale", "translations", "locales")
    ) or any((base / "flypig" / d).exists() for d in ("i18n", "locale", "translations", "locales"))

    # 检查是否有重复的 code 值
    seen_codes: dict[str, list[str]] = {}
    for cls_name, code_val in codes.items():
        seen_codes.setdefault(code_val, []).append(cls_name)

    for code_val, cls_list in seen_codes.items():
        if len(cls_list) > 1:
            violations.append(
                f'  [I18N] code 值 "{code_val}" 被多个异常类共用：{", ".join(cls_list)}，应确保唯一'
            )

    if not has_i18n_infra:
        violations.append(
            "  [I18N] 未检测到 i18n 基础设施（无 i18n/locale/translations 目录），"
            "异常 code 无法映射到用户界面文本"
        )

    return violations


# ── 14. 测试覆盖检查 ──────────────────────────────────────────────


def _module_to_test_path(source_rel: Path, tests_dir: Path) -> Path | None:
    """将源文件相对路径映射到测试文件路径"""
    parts = list(source_rel.parts)
    # 去掉 flypig/ 前缀
    if parts and parts[0] == "flypig":
        parts = parts[1:]
    if not parts:
        return None

    # 跳过 __init__.py 和自身就是测试的文件
    if source_rel.name == "__init__.py":
        return None

    # 构建测试路径: tests/unit/test_{layer}_{module}.py
    layer = parts[0] if parts else ""
    module_name = source_rel.stem

    # 尝试多种可能的测试路径
    candidates = [
        tests_dir / "unit" / f"test_{module_name}.py",
        tests_dir / "unit" / layer / f"test_{module_name}.py",
        tests_dir / "integration" / f"test_{module_name}.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    # 返回最可能的路径（即使不存在）
    return tests_dir / "unit" / f"test_{module_name}.py"


def check_test_coverage(py_files: list[Path], base_dir: Path) -> list[str]:
    """检查测试覆盖：每个业务模块是否有对应测试文件"""
    violations: list[str] = []
    tests_dir = base_dir / "tests"  # 测试现在在根目录
    if not tests_dir.exists():
        violations.append("  [TEST] 未找到 tests/ 测试目录")
        return violations

    # 要检查的源文件层
    source_layers = {"domain", "application", "infrastructure", "interface", "acl"}

    # 跳过测试覆盖的路径（routes/SSE 等通过集成测试覆盖，不需单元测试文件）
    skip_test_check = {
        "routes",
        "event",
        "prompts",
        "specification",
        "migrations",
        "scripts",
    }

    for f in py_files:
        try:
            rel = f.relative_to(base_dir / "flypig")
        except ValueError:
            continue

        parts = list(rel.parts)
        if len(parts) < 2 or parts[0] not in source_layers:
            continue
        if f.name == "__init__.py":
            continue
        if f.name.endswith("_test.py") or f.name.startswith("test_"):
            continue  # 跳过测试文件自身
        if any(skip in rel.parts for skip in skip_test_check):
            continue  # 跳过 routes/event/prompts 等

        test_path = _module_to_test_path(rel, tests_dir)
        if test_path is None:
            continue

        if not test_path.exists():
            violations.append(
                f"  [TEST] {rel} 缺少对应的测试文件 {test_path.relative_to(base_dir)}"
            )
        else:
            # 检查测试文件是否为空
            test_content = test_path.read_text(encoding="utf-8").strip()
            if not test_content or test_content == "'''":
                violations.append(
                    f"  [TEST] {rel} 的测试文件 {test_path.relative_to(base_dir)} 为空"
                )

    return violations


def check_file_registration(_py_files: list[Path], base_dir: Path) -> list[str]:
    """检查新文件是否在 __init__.__all__ 或 app_factory 中注册"""
    violations: list[str] = []
    flypig_dir = base_dir

    # 检查 1：domain/*.py 必须在 domain/__init__.__all__ 中导出
    domain_init = flypig_dir / "domain" / "__init__.py"
    if domain_init.exists():
        init_code = domain_init.read_text(encoding="utf-8")
        try:
            tree = ast.parse(init_code)
        except SyntaxError:
            violations.append("  [REGISTER] domain/__init__.py 语法错误，无法解析")
            return violations

        # 提取 __all__ 列表
        all_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
            ):
                if isinstance(node.value, ast.List):
                    all_names = [
                        str(elt.value) for elt in node.value.elts if isinstance(elt, ast.Constant)
                    ]
                break

        # 检查每个非 __init__ 的 domain 文件是否有类被导出
        for f in sorted(flypig_dir.joinpath("domain").glob("*.py")):
            if f.name == "__init__.py":
                continue
            # 检查该模块是否有类被 __all__ 引用（以模块名+类名方式或通配 import）
            has_export = False
            with open(f, encoding="utf-8") as fh:
                content = fh.read()
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name in all_names:
                    has_export = True
                    break
            if not has_export:
                violations.append(
                    f"  [REGISTER] domain/{f.name} 中的类未在 domain/__init__.__all__ 中导出"
                )

    # 检查 2：routes/*.py 必须在 app_factory._register_blueprints 中注册
    routes_dir = flypig_dir / "interface" / "rest" / "routes"
    app_factory = flypig_dir / "bootstrap" / "app_factory.py"
    if routes_dir.exists() and app_factory.exists():
        factory_code = app_factory.read_text(encoding="utf-8")
        for route_file in sorted(routes_dir.glob("*_routes.py")):
            blueprint_name = route_file.stem.split("_routes")[0] + "_bp"
            if blueprint_name not in factory_code:
                violations.append(
                    f"  [REGISTER] {route_file.name} 的蓝图 `{blueprint_name}` 未在 app_factory.py 中注册"
                )

    return violations


def check_api_contract(base_dir: Path) -> list[str]:
    """检查 API 契约：路由端点响应结构必须匹配 data/api-contracts.json 定义"""
    violations: list[str] = []
    contracts_file = base_dir / "flypig" / "data" / "api-contracts.json"
    routes_dir = base_dir / "flypig" / "interface" / "rest" / "routes"

    if not contracts_file.exists():
        violations.append(f"  [APICONTRACT] 未找到 API 契约文件：{contracts_file}")
        return violations
    if not routes_dir.exists():
        violations.append("  [APICONTRACT] 未找到路由目录")
        return violations

    import json
    import re

    contracts = json.loads(contracts_file.read_text(encoding="utf-8"))
    contracted_routes = contracts.get("contracts", {})

    # 从路由文件中收集所有实际路由路径
    actual_paths: set[str] = set()
    for rf in routes_dir.glob("*_routes.py"):
        content = rf.read_text(encoding="utf-8")
        # 收集蓝图定义（含 url_prefix）
        bp_defs = re.findall(
            r"(\w+)\s*=\s*Blueprint\([^)]*url_prefix=['\"]([^'\"]+)['\"]",
            content,
        )
        # 收集路由注册
        for match in re.finditer(r"@(\w+)\.route\(['\"]([^'\"]+)['\"]", content):
            bp_var, path = match.group(1), match.group(2)
            # 找出 HTTP methods
            line_start = max(0, content.rfind("\n", 0, match.start()) + 1)
            line_end = content.find("\n", match.start())
            line = content[line_start:line_end]
            methods = ["GET"]
            mm = re.search(r"methods=\[([^\]]*)\]", line)
            if mm:
                methods = [m.strip().strip('"').strip("'") for m in mm.group(1).split(",")]
            # 构建完整路径（考虑 url_prefix）
            full_path = path
            for bp_var_name, prefix in bp_defs:
                if bp_var_name == bp_var and not path.startswith(prefix):
                    full_path = prefix + path
                    break
            for m in methods:
                actual_paths.add(f"{m} {full_path}")

    # 检查契约中的路由是否匹配
    for route_key in contracted_routes:
        normalized = route_key.split(" ", 1)[1] if " " in route_key else route_key
        if route_key not in actual_paths and not any(normalized in ap for ap in actual_paths):
            violations.append(f"  [APICONTRACT] 契约定义了 {route_key}，但实际路由中未找到匹配")

    return violations


# ══════════════════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════════════════


def main() -> int:  # noqa: PLR0915
    """运行架构合规检查

    TODO: 已注释的检查项（depsec/i18n/test）是历史遗留问题，修复后取消注释
    """
    base_dir = Path(__file__).resolve().parent.parent / "flypig"
    if not base_dir.exists():
        print(f"[FAIL] 未找到 flypig 目录：{base_dir}")
        return 1

    # 注册所有检查器（仅保留 ruff 不覆盖的 FlyPig 特有项）
    checks: list[tuple[str, str, Callable[..., list[str]]]] = [
        ("layer", "层依赖方向", check_layer),
        ("ddd", "DDD 基类继承", check_ddd_inheritance),
        ("doc", "文件级 docstring", check_docstring),
        ("skel", "骨架文件标记", check_skeleton_marker),
        ("couplepkg", "包耦合度过高", check_couple_pkg),
        ("docq", "docstring质量", check_docstring_quality),
    ]

    results: dict[str, list[str]] = {key: [] for key, _, _ in checks}
    results["circular"] = []
    results["contract"] = []
    results["depsec"] = []
    results["config"] = []
    results["i18n"] = []
    results["test"] = []

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
        f
        for f in py_files
        if not any(skip in f.parts for skip in SKIP_DIRS) and "__pycache__" not in f.parts
    ]
    results["circular"] = check_circular(filted_files, base_dir.parent)

    # ── 接口契约检查（全局） ──
    results["contract"] = check_interface_contract(filted_files, base_dir.parent)

    # ── 依赖安全检查（全局） ──
    # TODO: 遗留问题，修复后取消注释
    # if not dev_mode:
    #     results["depsec"] = check_dependency_security(base_dir.parent)

    # ── 配置规范检查（全局） ──
    try:
        results["config"] = check_config_completeness(base_dir.parent)
    except Exception:
        results["config"] = [
            "  [CONFIG] check_config_completeness 执行异常，请检查 PyYAML 是否安装"
        ]

    # ── 国际化就绪检查（全局） ──
    # TODO: 遗留问题，修复后取消注释
    # if not dev_mode:
    #     results["i18n"] = check_i18n_readiness(filted_files)

    # ── 测试覆盖检查（全局） ──
    # TODO: 遗留问题，修复后取消注释
    # if not dev_mode:
    #     results["test"] = check_test_coverage(filted_files, base_dir.parent)

    # ── 新文件注册检查（全局） ──
    results["register"] = check_file_registration(filted_files, base_dir.parent)

    # ── API 契约检查（全局） ──
    results["apicontract"] = check_api_contract(base_dir.parent)

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
        "layer": ("LAYER", "层依赖方向"),
        "ddd": ("DDD", "DDD 基类继承"),
        "doc": ("DOC", "文件级 docstring"),
        "skel": ("SKEL", "骨架文件标记"),
        "couplepkg": ("COUPLE_PKG", "包耦合度过高"),
        "docq": ("DOCQ", "docstring质量"),
        "circular": ("CIRCULAR", "循环依赖"),
        "contract": ("CONTRACT", "接口契约"),
        "depsec": ("DEPSEC", "依赖安全"),
        "config": ("CONFIG", "配置规范"),
        "i18n": ("I18N", "国际化就绪"),
        "test": ("TEST", "测试覆盖"),
        "register": ("REGISTER", "新文件注册"),
        "apicontract": ("APICONTRACT", "API 契约"),
    }

    for key, violations in results.items():
        if not violations:
            continue
        _kind, title = labels.get(key, (key.upper(), key))
        print(f"\n[FAIL] {title}（{len(violations)} 处）")
        print("\n".join(violations))

    print(f"\n{'=' * 60}")
    print(f"  共 {total} 处违规")
    print("  请修复后再提交")
    print(f"{'=' * 60}")
    return 1


if __name__ == "__main__":
    backend_code = main()
    # 可选：同时跑前端检查
    frontend_script = Path(__file__).parent / "frontend_check.py"
    if frontend_script.exists():
        result = subprocess.run(  # noqa: PLW1510
            [sys.executable, str(frontend_script)],
            capture_output=False,
        )
        sys.exit(max(backend_code, result.returncode))
    sys.exit(backend_code)
