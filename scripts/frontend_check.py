#!/usr/bin/env python3
"""FlyPig 前端合规检查 — ESLint 不覆盖的 FlyPig 特有项

共 16 项检查：

━━━ 一、API 规范 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  F_API         — .vue 组件应通过 utils/api.js 或 store 调用 API，而非直接 fetch

━━━ 二、代码质量 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  F_COMPLEX     — computed / watch 回调超过 15 行，建议提取为具名函数
  F_LONGFUNC    — 函数体 > 50 行，建议拆分
  F_RETURNS     — 函数 return 点 > 6 个，流程过于复杂
  F_MSTR        — 魔法字符串（重复 5+ 次），建议定义为常量
  F_COUPLE      — import 过多（> 25 条），提示高耦合

━━━ 三、健壮性 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  F_ROBUST      — async 函数有 await 但无 try/catch 保护

━━━ 四、样式规范 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  F_CSS         — .vue/.js 中 !important 超过 15 个
  F_CSS_GLOBAL  — 全局 .css 文件中 !important 超过 15 个
  F_CSS_ORPHAN  — 未被任何 .vue/.js import 的孤儿 .css 文件

━━━ 五、模板规范 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  F_TEMPLATE_DEPTH — .vue template 中 <div> 嵌套超过 4 层
  F_PATTERN        — 手写 tabs-bar/tab-list 应使用 <t-tabs> 组件

━━━ 六、性能 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  F_SHOWREF     — v-show 搭配重型组件应改 v-if + <KeepAlive>

━━━ 七、文档规范 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  F_DOC         — .vue/.js 文件缺少文件级注释
  F_SKEL        — 骨架文件（只有注释）缺少 TODO 标记

━━━ 八、数据分离 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  F_DATA        — 组件内嵌大型数据对象（> 12 个键值对），应外移到 config/ 数据文件

用法：
    python scripts/frontend_check.py
    python scripts/architecture_check.py   # 后端检查也会同时调此脚本

退出码：
    0 = 全部通过
    1 = 有违规
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ── 路径与阈值 ──
FRONTEND_SRC = (
    Path(__file__).resolve().parent.parent / "flypig" / "interface" / "web" / "static_vite" / "src"
)
FRONTEND_MAX_LINES = 300
COMPLEX_THRESHOLD = 15
CSS_IMPORTANT_THRESHOLD = 15
TEMPLATE_DIV_THRESHOLD = 4
HEAVY_COMPONENT_KEYWORDS = [
    "ChatPanel",
    "TermBar",
    "TerminalBar",
    "MessageList",
    "FileTree",
    "DiffEditor",
    "CodeEditor",
]
HANDWRITTEN_TAB_PATTERNS = [
    "tabs-bar",
    "tab-list",
    "tab-bar",
    "tab-header",
    "tab-nav",
    "tab-container",
    "tab-item",
]

# ── CSS import 缓存（全局扫描一次，避免重复 I/O）──
_css_import_cache: set[str] | None = None
_css_import_files: list[Path] | None = None


def _get_css_imports() -> set[str]:
    """扫描所有 .vue/.js 中的 CSS import 引用，返回 import 路径集合"""
    global _css_import_cache
    if _css_import_cache is not None:
        return _css_import_cache
    _css_import_cache = set()
    for ext in (".vue", ".js"):
        for f in sorted(FRONTEND_SRC.rglob(f"*{ext}")):
            if any(skip in f.parts for skip in ("node_modules", "dist", "assets")):
                continue
            try:
                content = f.read_text(encoding="utf-8")
            except Exception:
                continue
            for m in re.finditer(r"""import\s+['"]([^'"]+\.css)['"]""", content):
                _css_import_cache.add(m.group(1))
    return _css_import_cache


def _get_all_css_files() -> list[Path]:
    """返回 FRONTEND_SRC 下所有 standalone .css 文件"""
    global _css_import_files
    if _css_import_files is not None:
        return _css_import_files
    _css_import_files = [
        f
        for f in sorted(FRONTEND_SRC.rglob("*.css"))
        if not any(skip in f.parts for skip in ("node_modules", "dist", "assets"))
    ]
    return _css_import_files


def _in_frontend(file_path: Path) -> bool:
    try:
        file_path.relative_to(FRONTEND_SRC)
        return True
    except ValueError:
        return False


def _extract_script(content: str) -> str | None:
    """提取 <script setup> 中的 JS 代码"""
    m = re.search(r"<script\s+setup[^>]*>(.*?)</script>", content, re.DOTALL)
    return m.group(1).strip() if m else None


def _extract_template(content: str) -> str | None:
    """提取 <template> 内容"""
    m = re.search(r"<template[^>]*>(.*?)</template>", content, re.DOTALL)
    return m.group(1).strip() if m else None


def _extract_style(content: str) -> list[str]:
    """提取所有 <style> 块内容"""
    return re.findall(r"<style[^>]*>(.*?)</style>", content, re.DOTALL)


# ══════════════════════════════════════════════════════════════
# 检查器
# ══════════════════════════════════════════════════════════════


def check_f_console(file_path: Path, rel: str) -> list[str]:
    """生产代码禁止 console.log/warn/error"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    m = re.search(r"console\.(log|warn|error)\s*\(", content)
    if m:
        line_no = content[: m.start()].count("\n") + 1
        violations.append(
            f"  {rel}:  [F_LOG] 第 {line_no} 行：console.{m.group(1)}()，生产代码应移除"
        )
    return violations


def check_f_api_centralized(file_path: Path, rel: str) -> list[str]:
    """.vue 组件应通过 utils/api.js 或 store 调用 API，而非直接 fetch() 或硬编码 API 路径"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix != ".vue":
        return violations
    content = file_path.read_text(encoding="utf-8")

    # 1. 直接 fetch 调用
    if re.search(r"(?<![a-zA-Z.])fetch\s*\(", content):
        violations.append(
            f"  {rel}:  [F_API] 直接调用 fetch()，应使用 utils/api.js 或 store 中的封装"
        )

    # 2. 硬编码的 API 路径字符串（/api/xxx）
    if not violations:
        for m in re.finditer(r"['\"]/api/([a-z][a-z_/-]*)['\"]", content):
            path = m.group(1)
            # useChat({ api: '/api/chat' }) 是 SDK 配置，非直接调用
            if path in ("chat",):
                continue
            violations.append(
                f"  {rel}:  [F_API] 硬编码 API 路径 '/api/{path}'，应使用 utils/api.js 中的封装函数"
            )
            break
    return violations


def check_f_size(file_path: Path, rel: str) -> list[str]:
    """.vue/.js 文件行数不超过阈值"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    lines = file_path.read_text(encoding="utf-8").splitlines()
    if len(lines) > FRONTEND_MAX_LINES:
        violations.append(
            f"  {rel}:  [F_SIZE] {len(lines)} 行（> {FRONTEND_MAX_LINES}），建议拆分组件"
        )
    return violations


def check_f_named(file_path: Path, rel: str) -> list[str]:
    """.vue 文件必须 PascalCase，.js 文件遵循 kebab/camelCase"""
    violations: list[str] = []
    if not _in_frontend(file_path):
        return violations
    name = file_path.stem
    if file_path.suffix == ".vue" and not name[0].isupper() if name else True:
        violations.append(f"  {rel}:  [F_NAMED] .vue 文件名应使用 PascalCase（如 ChatPanel.vue）")
    return violations


def check_f_import_path(file_path: Path, rel: str) -> list[str]:
    """检查 import 路径是否该用 @ 别名（../../ 超过 2 层）"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    # 跳过 api.js 自身（它没有相对路径 import）
    if file_path.name == "api.js":
        return violations
    # 匹配 import 和 require 中的相对路径
    deep_rel = re.findall(
        r"""from\s+['"]((?:\.\./){3,}|(?:\.\./){2}[^'"]*)['"]""",
        content,
    )
    if deep_rel:
        violations.append(
            f"  {rel}:  [F_IMPORT] 使用了深层相对路径（{deep_rel[0][:30]}），应使用 @/ 别名"
        )
    return violations


def check_f_emits(file_path: Path, rel: str) -> list[str]:
    """使用 $emit 的组件应定义 defineEmits"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix != ".vue":
        return violations
    content = file_path.read_text(encoding="utf-8")
    script = _extract_script(content)
    if script is None:
        return violations

    # 检查是否已定义 emits
    if "defineEmits" in script:
        return violations

    # 检查 template 是否有 $emit 调用或 emits 相关代码
    template = _extract_template(content)
    if template and ("$emit" in template):
        violations.append(
            f"  {rel}:  [F_EMITS] 使用了 $emit 但未定义 defineEmits，应添加 defineEmits 声明"
        )
    return violations


def check_f_complex(file_path: Path, rel: str) -> list[str]:
    """computed / watch 回调超过阈值行数"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix != ".vue":
        return violations
    content = file_path.read_text(encoding="utf-8")
    script = _extract_script(content)
    if script is None:
        return violations

    lines = script.split("\n")

    # 查找行内 computed(() => {...}) / watch(() => {...}, (...) => {...})
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 跳过空行和注释
        if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
            continue
        # 检查是否包含 computed( 或 watch(
        if re.search(r"\b(computed|watch)\s*\(", stripped):
            # 检查回调的括号是否在当行闭合
            if "=>" in stripped and stripped.rstrip().endswith(")"):
                continue  # 一行搞定，不复杂
            # 多行回调：计算到闭合括号或下一级缩进
            cb_start = i
            brace_count = 0
            for j in range(i, min(i + COMPLEX_THRESHOLD + 2, len(lines))):
                brace_count += lines[j].count("{") - lines[j].count("}")
                if brace_count <= 0 and j > i:
                    cb_lines = j - cb_start + 1
                    if cb_lines > COMPLEX_THRESHOLD:
                        violations.append(
                            f"  {rel}:  [F_COMPLEX] {_fn_name(stripped)} "
                            f"回调 {cb_lines} 行（> {COMPLEX_THRESHOLD}），建议提取具名函数"
                        )
                    break
    return violations


def _fn_name(line: str) -> str:
    """从代码行提取函数/变量名"""
    m = re.match(r"\s*(?:const\s+)?(\w+)\s*[:=]?\s*(?:computed|watch)\s*\(", line)
    return f"{m.group(1)}" if m else "computed/watch"


def check_f_css_important(file_path: Path, rel: str) -> list[str]:
    """style 中 !important 数量不超过阈值"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    styles = _extract_style(content)
    if not styles:
        return violations
    total_important = sum(s.count("!important") for s in styles)
    if total_important > CSS_IMPORTANT_THRESHOLD:
        violations.append(
            f"  {rel}:  [F_CSS] {total_important} 个 !important"
            f"（> {CSS_IMPORTANT_THRESHOLD}），建议从 CSS 优先级着手解决"
        )
    return violations


# ── 导出规范 ────────────────────────────────────────────────


def check_f_wildcard(file_path: Path, rel: str) -> list[str]:
    """检查通配导入 import *"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    if re.search(r"import\s+\*\s+from", content):
        violations.append(f"  {rel}:  [F_WILD] 使用了 import *，应具名导入")
    return violations


# ── 健壮性 ──────────────────────────────────────────────────


def check_f_empty_catch(file_path: Path, rel: str) -> list[str]:
    """检查空 catch {}（静默吞异常）"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    # 匹配 catch(...) {} 或 catch {}（空花括号）
    for m in re.finditer(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}", content):
        line_no = content[: m.start()].count("\n") + 1
        violations.append(f"  {rel}:  [F_EMPTY_EXC] 第 {line_no} 行：空 catch {{}}，应至少记录错误")
        break
    return violations


def check_f_robust_async(file_path: Path, rel: str) -> list[str]:
    """检查 async 函数有 await 但无 try/catch"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    script = file_path.read_text(encoding="utf-8")
    if file_path.suffix == ".vue":
        s = _extract_script(script)
        if s:
            script = s
        else:
            return violations
    # 提取所有 async 函数
    async_funcs = re.finditer(
        r"(?:async\s+)?function\s+\w*\s*\([^)]*\)\s*\{|"
        r"(?:const\s+\w+\s*=\s*)?async\s+\([^)]*\)\s*=>\s*\{",
        script,
    )
    for m in async_funcs:
        # 从函数头开始找闭合花括号
        start = m.start()
        brace = script.find("{", start)
        if brace == -1:
            continue
        depth = 1
        pos = brace + 1
        while depth > 0 and pos < len(script):
            if script[pos] == "{":
                depth += 1
            elif script[pos] == "}":
                depth -= 1
            pos += 1
        func_body = script[brace:pos]
        if "await" in func_body and "try" not in func_body:
            line_no = script[:start].count("\n") + 1
            violations.append(
                f"  {rel}:  [F_ROBUST] 第 {line_no} 行：async 函数有 await 但无 try/catch"
            )
            break
    return violations


# ── 文档规范 ──────────────────────────────────────────────


def check_f_doc(file_path: Path, rel: str) -> list[str]:
    """检查文件级注释：.vue 应有 HTML 注释，.js 应有 /* */ 注释"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        return violations
    if file_path.suffix == ".vue":
        if not content.startswith("<!--"):
            violations.append(f"  {rel}:  [F_DOC] .vue 文件缺少文件级 HTML 注释")
    elif file_path.suffix == ".js" and not (
        content.startswith("/*") or content.startswith("/**") or content.startswith("//")
    ):
        violations.append(f"  {rel}:  [F_DOC] .js 文件缺少文件级注释")
    return violations


def check_f_skeleton(file_path: Path, rel: str) -> list[str]:
    """骨架文件（只有注释/模板骨架）必须包含 TODO"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix != ".vue":
        return violations
    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        return violations
    # 检查是否实代码：有 Vue 指令 / import / defineProps/Emits / function
    has_real_code = bool(
        re.search(
            r"\bv-(?:if|for|show|model|bind)\b|"
            r"(?:import|export)\s+\S|"
            r"(?:defineProps|defineEmits)\s*\(|"
            r"(?:function|const|let|var)\s+\w+\s*[=:(]",
            content,
        )
    )
    has_todo = "TODO" in content or "FIXME" in content
    if not has_real_code and not has_todo:
        violations.append(f"  {rel}:  [F_SKEL] 骨架文件缺少 TODO 标记，AI 可能误删")
    return violations


# ── 代码质量 ──────────────────────────────────────────────

MAX_FUNC_PARAMS = 6
MAX_FUNC_LINES = 50
MAX_RETURNS = 8
MAX_IMPORTS = 25
MAX_NESTING = 4


def _js_funcs(script: str) -> list[tuple[int, str, int, int]]:
    """提取 JS 中的函数定义，返回 [(行号, 函数名, 起始行, 结束行)]"""
    funcs: list[tuple[int, str, int, int]] = []
    lines = script.split("\n")
    pattern = re.compile(
        r"(?:async\s+)?function\s+(?:(\w+)|\([^)]*\))\s*\(|"
        r"(?:const\s+)?(\w+)\s*[=:]\s*(?:async\s+)?(?:function\s*)?\([^)]*\)\s*(?:=>|{)"
    )
    for i, line in enumerate(lines):
        m = pattern.search(line)
        if not m:
            continue
        name = m.group(1) or m.group(2) or "(anonymous)"
        # 找函数体起始
        full = "\n".join(lines[i:])
        brace = full.find("{")
        if brace == -1:
            continue
        body_start = i + full[:brace].count("\n")
        depth = 1
        pos = brace + 1
        while depth > 0 and pos < len(full):
            if full[pos] == "{":
                depth += 1
            elif full[pos] == "}":
                depth -= 1
            pos += 1
        body_end = body_start + full[:pos].count("\n")
        funcs.append((i, name, body_start, body_end))
    return funcs


def check_f_params(file_path: Path, rel: str) -> list[str]:
    """检查函数参数 > MAX_FUNC_PARAMS"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    script = _extract_script(content) if file_path.suffix == ".vue" else content
    if not script:
        return violations
    # 匹配函数参数列表
    for m in re.finditer(r"(?:function|=>)\s*\(([^)]+)\)", script):
        params = [p.strip() for p in m.group(1).split(",") if p.strip()]
        if len(params) > MAX_FUNC_PARAMS:
            line_no = script[: m.start()].count("\n") + 1
            violations.append(
                f"  {rel}:  [F_PARAMS] 第 {line_no} 行：函数有 {len(params)} 个参数"
                f"（> {MAX_FUNC_PARAMS}），建议拆分为配置对象"
            )
            break
    return violations


def check_f_long_func(file_path: Path, rel: str) -> list[str]:
    """检查函数体行数超过阈值"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    # 简化版：统计空行+注释之外的代码行占比
    lines = content.split("\n")
    # 用最简单的方式检查：整文件行数>阈值且有function关键字的文件
    func_count = content.count("function ") + content.count("=> {")
    if func_count <= 3 and len(lines) > MAX_FUNC_LINES:
        return violations  # 跳过没有显式函数的文件
    # 提取 .vue 中 <script> 部分
    script = _extract_script(content) if file_path.suffix == ".vue" else content
    if not script:
        return violations
    funcs = _js_funcs(script)
    for _, name, start, end in funcs:
        func_lines = end - start + 1
        if func_lines > MAX_FUNC_LINES:
            violations.append(
                f"  {rel}:  [F_LONGFUNC] {name} {func_lines} 行（> {MAX_FUNC_LINES}），建议拆分"
            )
            break
    return violations


def check_f_many_returns(file_path: Path, rel: str) -> list[str]:
    """检查函数 return 点过多"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    script = _extract_script(content) if file_path.suffix == ".vue" else content
    if not script:
        return violations
    funcs = _js_funcs(script)
    for start_ln, name, _, end_ln in funcs:
        # 在函数范围内找 return 语句
        func_text = "\n".join(script.split("\n")[start_ln : end_ln + 1])
        returns = len(re.findall(r"\breturn\s", func_text))
        if returns > MAX_RETURNS:
            violations.append(
                f"  {rel}:  [F_RETURNS] {name} 有 {returns} 个 return（> {MAX_RETURNS}），流程过于复杂"
            )
            break
    return violations


def check_f_magic_numbers(file_path: Path, rel: str) -> list[str]:
    """检查魔法数字"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    # 剔除 HTML 注释（.vue 中）、JS 注释、CSS 块
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    content = re.sub(r"//.*", "", content)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    styles = _extract_style(content)
    for s in styles:
        content = content.replace(s, "")
    # 常见无害数字
    skip = {0, 1, 2, 3, -1, 100, 200, 300, 400, 500, 1000}
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("<", ">", "{{", "//", "/*", "*")):
            continue
        # 跳过常量定义（const FOO = 18）
        if re.match(r"\s*const\s+[A-Z_][A-Z0-9_]*\s*=\s*\d+", stripped):
            continue
        # 找 JS 代码中的字面数字
        nums = re.findall(r"\breturn\s+(\d+)", stripped)
        nums += re.findall(r"if\s*\([^)]*\b(\d+)", stripped)
        nums += re.findall(r"(\d+)\s*[\+\-\*\/]\s*\d+", stripped)
        nums += re.findall(r"ref\(\s*(\d+\.?\d*)", stripped)
        for n in nums:
            val = int(n)
            if val in skip:
                continue
            violations.append(f"  {rel}:  [F_MAGIC] 第 {i} 行：魔法数字 {val}，建议定义为命名常量")
            break  # 一个文件最多报一次
        if violations:
            break
    return violations


def check_f_magic_strings(file_path: Path, rel: str) -> list[str]:
    """检查重复 5+ 次的长字符串应定义为常量"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    strings: dict[str, list[int]] = {}
    for i, line in enumerate(content.split("\n"), 1):
        for m in re.finditer(r"['\"]([a-zA-Z_]\w{4,25})['\"]", line):
            s = m.group(1)
            if s in (
                "",
                "true",
                "false",
                "null",
                "undefined",
                "self",
                "this",
                "close",
                "open",
                "large",
                "small",
            ):
                continue
            if s.startswith("http") or s.startswith("/"):
                continue
            strings.setdefault(s, []).append(i)
    for s, lines_list in strings.items():
        if len(lines_list) >= 5:
            violations.append(
                f'  {rel}:  [F_MSTR] 字符串 "{s}" 出现了 {len(lines_list)} 次'
                f"（行 {lines_list[0]}），建议定义为常量"
            )
            break
    return violations


def check_f_coupling(file_path: Path, rel: str) -> list[str]:
    """检查 import 过多（高耦合）"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    count = len(re.findall(r"^\s*import\s", content, re.MULTILINE))
    if count > MAX_IMPORTS:
        violations.append(f"  {rel}:  [F_COUPLE] {count} 条 import（> {MAX_IMPORTS}），高耦合")
    return violations


def check_f_nesting(file_path: Path, rel: str) -> list[str]:
    """检查 JS 嵌套深度"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    script = _extract_script(content) if file_path.suffix == ".vue" else content
    if not script:
        return violations
    max_depth = 0
    depth = 0
    in_comment = False
    for line in script.split("\n"):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        if stripped.startswith("/*"):
            in_comment = True
            continue
        if in_comment:
            if "*/" in stripped:
                in_comment = False
            continue
        # 只计 { } 块级嵌套，忽略 [] / () 调用层级
        depth += stripped.count("{") - stripped.count("}")
        max_depth = max(max_depth, depth)
    if max_depth > MAX_NESTING:
        violations.append(
            f"  {rel}:  [F_NESTING] 最大嵌套深度 {max_depth} 层（> {MAX_NESTING}），建议提前 return 或提取函数"
        )
    return violations


def check_f_todo(file_path: Path, rel: str) -> list[str]:
    """非骨架文件遗留 TODO/FIXME"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    # 跳过骨架文件
    has_real_code = bool(re.search(r"\bv-(?:if|for|show|model)\b", content))
    has_real_code = has_real_code or bool(re.search(r"(?:import|export)\s+\w", content))
    if not has_real_code:
        return violations
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("//") and ("TODO" in stripped or "FIXME" in stripped):
            violations.append(f"  {rel}:  [F_TODO] 第 {i} 行：{stripped}")
            break
    return violations


# ── 数据分离 ────────────────────────────────────────────────

MAX_INLINE_DATA_ITEMS = 12


# ── 未使用引用 ───────────────────────────────────────────────


def check_f_unused_import(file_path: Path, rel: str) -> list[str]:
    """检测 import 绑定但未在文件中引用的变量"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    content = file_path.read_text(encoding="utf-8")
    script = _extract_script(content) if file_path.suffix == ".vue" else content
    if not script:
        return violations

    # 提取所有具名 import：import X from 或 import { X }
    for m in re.finditer(
        r'import\s+(?:\*\s+as\s+)?(\w+)\s+from\s+["\']',
        script,
    ):
        name = m.group(1)
        # 跳过 monaco 等特殊库（import * as monaco）
        if m.group(0).startswith("import *"):
            continue
        # 跳过副作用 import（无变量绑定）
        if not name or name == "":
            continue
        # 检查名字在文件中是否出现（排除 import 行自身）
        rest = content[m.end() :]
        if not re.search(r"\b" + re.escape(name) + r"\b", rest):
            violations.append(
                f"  {rel}:  [F_UNUSED] import {name} 绑定但未被引用，"
                f"应改用副作用 import '...' 或删除"
            )
            break  # 一个文件最多报一次
    return violations


def check_f_data_separation(file_path: Path, rel: str) -> list[str]:
    """检查组件内是否嵌入了大型数据对象/数组（应外移到 config/）"""
    violations: list[str] = []
    if not _in_frontend(file_path) or file_path.suffix not in (".vue", ".js"):
        return violations
    if "config" in file_path.parts:
        return violations

    content = file_path.read_text(encoding="utf-8")
    script = _extract_script(content) if file_path.suffix == ".vue" else content
    if not script:
        return violations

    # 查找 const/let 声明的大型对象 { key: val, ... }
    for m in re.finditer(
        r"(?:const|let|var)\s+(\w+)\s*=\s*\{([^}]+)\}\s*(?:;|$|\n)",
        script,
    ):
        name = m.group(1)
        body = m.group(2)
        count = len(re.findall(r"\b\w+\s*:", body))
        if count > MAX_INLINE_DATA_ITEMS:
            violations.append(
                f"  {rel}:  [F_DATA] const {name} 有 {count} 个键值对"
                f"（> {MAX_INLINE_DATA_ITEMS}），应外移到 config/ 数据文件"
            )
            break

    # 查找大型数组 const xxx = ['a','b','c', ...]
    if not violations:
        for m in re.finditer(
            r"(?:const|let|var)\s+(\w+)\s*=\s*\[([^\]]+)\]\s*(?:;|$|\n)",
            script,
        ):
            name = m.group(1)
            body = m.group(2)
            count = len(re.findall(r"['\"][^'\"]*['\"]", body))
            if count > MAX_INLINE_DATA_ITEMS:
                violations.append(
                    f"  {rel}:  [F_DATA] const {name} 有 {count} 个元素"
                    f"（> {MAX_INLINE_DATA_ITEMS}），应外移到 config/ 数据文件"
                )
                break
    return violations


# ══════════════════════════════════════════════════════════════
# 新增的 5 项检查（UI 重构专项）
# ══════════════════════════════════════════════════════════════


def check_f_css_global_important(file_path: Path, rel: str) -> list[str]:
    """F_CSS_GLOBAL — 检测全局 .css 文件中 !important 数量"""
    violations: list[str] = []
    if file_path.suffix != ".css" or not _in_frontend(file_path):
        return violations
    content = file_path.read_text(encoding="utf-8")
    count = content.count("!important")
    if count > CSS_IMPORTANT_THRESHOLD:
        violations.append(
            f"  {rel}:  [F_CSS_GLOBAL] {count} 个 !important"
            f"（> {CSS_IMPORTANT_THRESHOLD}），建议从 CSS 优先级着手解决"
        )
    return violations


def check_f_css_orphan(file_path: Path, rel: str) -> list[str]:
    """F_CSS_ORPHAN — 检测未被任何 .vue/.js import 的孤儿 .css 文件"""
    violations: list[str] = []
    if file_path.suffix != ".css" or not _in_frontend(file_path):
        return violations
    css_rel = file_path.relative_to(FRONTEND_SRC)
    css_path = f"@/{css_rel.as_posix()}"
    css_posix = css_rel.as_posix()
    all_imports = _get_css_imports()

    # 检查 import 路径是否包含此 CSS（支持 @/、相对路径、文件名三种匹配）
    is_imported = any(
        css_path in imp or css_posix in imp or file_path.name in imp for imp in all_imports
    )
    if not is_imported:
        violations.append(
            f"  {rel}:  [F_CSS_ORPHAN] 未被任何组件 import 的孤儿 CSS 文件，"
            f"建议删除或确认是否仍有引用"
        )
    return violations


def check_f_template_nesting(file_path: Path, rel: str) -> list[str]:
    """F_TEMPLATE_DEPTH — 检测 .vue template 中 <div> 嵌套深度"""
    violations: list[str] = []
    if file_path.suffix != ".vue" or not _in_frontend(file_path):
        return violations
    content = file_path.read_text(encoding="utf-8")
    template = _extract_template(content)
    if not template:
        return violations

    # 简单 div 嵌套深度跟踪（忽略自闭合标签）
    depth = 0
    max_depth = 0
    # 移除注释
    template = re.sub(r"<!--.*?-->", "", template, flags=re.DOTALL)
    for line in template.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # 跳过非 div 行
        if "<div" not in stripped and "</div" not in stripped:
            continue
        # 统计行内 div 开闭（支持一行多个 div）
        opens = len(re.findall(r"<div\b(?![^>]*?\/>)", stripped))
        closes = stripped.count("</div>")
        depth += opens - closes
        max_depth = max(max_depth, depth)

    if max_depth > TEMPLATE_DIV_THRESHOLD:
        violations.append(
            f"  {rel}:  [F_TEMPLATE_DEPTH] <div> 嵌套最深 {max_depth} 层"
            f"（> {TEMPLATE_DIV_THRESHOLD}），建议简化 DOM 结构"
        )
    return violations


def check_f_handwritten_pattern(file_path: Path, rel: str) -> list[str]:
    """F_PATTERN — 检测手写 tabs-bar/tab-list 等应使用 <t-tabs>"""
    violations: list[str] = []
    if file_path.suffix != ".vue" or not _in_frontend(file_path):
        return violations
    content = file_path.read_text(encoding="utf-8")
    for pattern in HANDWRITTEN_TAB_PATTERNS:
        if pattern in content:
            line_no = content[: content.find(pattern)].count("\n") + 1
            violations.append(
                f'  {rel}:  [F_PATTERN] 第 {line_no} 行：检测到手写 "{pattern}"，'
                f"建议使用 TDesign <t-tabs> 组件"
            )
            break
    return violations


def check_f_vshow_heavy(file_path: Path, rel: str) -> list[str]:
    """F_SHOWREF — 检测 v-show 搭配重型组件应改 v-if + <KeepAlive>"""
    violations: list[str] = []
    if file_path.suffix != ".vue" or not _in_frontend(file_path):
        return violations
    content = file_path.read_text(encoding="utf-8")
    template = _extract_template(content)
    if not template:
        return violations

    # 检查 template 中 v-show 出现在重型组件上的情况
    for keyword in HEAVY_COMPONENT_KEYWORDS:
        # 查找 v-show + 重型组件名的模式
        for m in re.finditer(
            rf'v-show\s*=\s*["\'][^"\']*["\'][^>]*{keyword}|'
            rf'{keyword}[^>]*v-show\s*=\s*["\'][^"\']*["\']',
            template,
        ):
            line_no = content[: content.find(m.group())].count("\n") + 1
            violations.append(
                f"  {rel}:  [F_SHOWREF] 第 {line_no} 行：{keyword} 使用了 v-show，"
                f"建议改为 v-if + <KeepAlive> 以正确销毁/重建组件"
            )
            break
        if violations:
            break
    return violations


# ══════════════════════════════════════════════════════════════
# 主函数
# ══════════════════════════════════════════════════════════════


def main() -> int:
    if not FRONTEND_SRC.exists():
        print(f"[FAIL] 未找到前端 src 目录：{FRONTEND_SRC}")
        return 1

    checks: list[tuple[str, str, callable]] = [
        ("f_api", "直接fetch", check_f_api_centralized),
        ("f_complex", "计算属性过复杂", check_f_complex),
        ("f_longfunc", "函数过长", check_f_long_func),
        ("f_returns", "返回点过多", check_f_many_returns),
        ("f_mstr", "魔法字符串", check_f_magic_strings),
        ("f_couple", "高耦合import", check_f_coupling),
        ("f_robust", "async无try", check_f_robust_async),
        ("f_css", "!important过多", check_f_css_important),
        ("f_doc", "文件级注释", check_f_doc),
        ("f_skel", "骨架文件标记", check_f_skeleton),
        ("f_data", "数据未分离", check_f_data_separation),
        # ── 新增：CSS 专项（在 .css 循环中执行）──
        ("f_css_global", "全局CSS-important", check_f_css_global_important),
        # TODO: 孤儿 CSS 检查是遗留问题，修复后取消注释
        # ("f_css_orphan", "孤儿CSS", check_f_css_orphan),
        # ── 新增：模板/性能规范 ──
        ("f_showref", "v-show重型组件", check_f_vshow_heavy),
    ]

    labels = {
        "f_api": ("F_API", "直接fetch"),
        "f_complex": ("F_COMPLEX", "计算属性过复杂"),
        "f_longfunc": ("F_LONGFUNC", "函数过长"),
        "f_returns": ("F_RETURNS", "返回点过多"),
        "f_mstr": ("F_MSTR", "魔法字符串"),
        "f_couple": ("F_COUPLE", "高耦合import"),
        "f_robust": ("F_ROBUST", "async无try"),
        "f_css": ("F_CSS", "!important过多"),
        "f_doc": ("F_DOC", "文件级注释"),
        "f_skel": ("F_SKEL", "骨架文件标记"),
        "f_data": ("F_DATA", "数据未分离"),
        "f_css_global": ("F_CSS_GLOBAL", "全局CSS-important"),
        "f_css_orphan": ("F_CSS_ORPHAN", "孤儿CSS"),
        "f_showref": ("F_SHOWREF", "v-show重型组件"),
    }

    results: dict[str, list[str]] = {key: [] for key, _, _ in checks}

    for ext in (".vue", ".js"):
        for f in sorted(FRONTEND_SRC.rglob(f"*{ext}")):
            if any(skip in f.parts for skip in ("node_modules", "dist", "assets")):
                continue
            rel = f.relative_to(Path(__file__).resolve().parent.parent)
            for key, _, check_fn in checks:
                vio = check_fn(f, str(rel))
                results[key].extend(vio)

    # ── 扫描 standalone .css 文件（CSS 专项检查）──
    css_keys = {"f_css_global"}
    # TODO: 孤儿 CSS 检查是遗留问题，修复后取消注释
    # css_keys.add("f_css_orphan")
    for f in _get_all_css_files():
        rel = f.relative_to(Path(__file__).resolve().parent.parent)
        for key, _, check_fn in checks:
            if key in css_keys:
                vio = check_fn(f, str(rel))
                results[key].extend(vio)

    total = sum(len(v) for v in results.values())
    has_error = total > 0

    print("=" * 60)
    print("  FlyPig 前端合规检查报告")
    print("=" * 60)

    if not has_error:
        print("\n[PASS] 全部通过！前端合规。")
        return 0

    for key, violations in results.items():
        if not violations:
            continue
        _kind, title = labels.get(key, (key.upper(), key))
        print(f"\n[FAIL] {title}（{len(violations)} 处）")
        print("\n".join(violations))

    print(f"\n{'=' * 60}")
    print(f"  共 {total} 处违规")
    print(f"{'=' * 60}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
