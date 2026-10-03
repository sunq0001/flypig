"""代码规范自动检查工具

为什么做：AI 改完代码后自动检查 ruff/eslint/architecture 规范，将结果喂回 chat 节点，
         LLM 看到错误后自动修复，形成 "写代码 → 检查 → 修复" 的自愈循环。

实现方法：
  - run_ruff(path)：调用 ruff check，返回错误列表
  - run_eslint(path)：调用 npx eslint，返回错误列表（前端文件）
  - run_architecture()：调用 architecture_check.py，返回架构违规
  - __call__ 方法根据文件后缀自动选择检查器

实现效果：AI 输出的代码自动符合规范，不需要用户反馈 lint 错误。
技术栈：subprocess ruff --fix, eslint, architecture_check

层&依赖：infrastructure.tools.review 层，依赖 subprocess
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from flypig.infrastructure.tools.registry import tool
from flypig.infrastructure.tools.review.lint_parser import (
    parse_eslint_output,
    parse_ruff_output,
)

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # → flypig-agent/

# ── 工具名 / 检查器名 ──
_TOOL_NAME = "run_linter"
_CHECKER_RUFF = "ruff"
_CHECKER_ESLINT = "eslint"
_CHECKER_ARCH = "architecture_check"

# ── 结果 JSON 的字段名 ──
_KEY_TOOL = "tool"
_KEY_CHECKER = "checker"
_KEY_TARGET = "target"
_KEY_STATUS = "status"
_KEY_ERRORS = "errors"
_KEY_STDERR = "stderr"
_STATUS_PASSED = "passed"
_STATUS_FAILED = "failed"

# ── 超时 / 支持的文件类型 ──
_RUFF_TIMEOUT = 30
_ESLINT_TIMEOUT = 30
_ARCH_TIMEOUT = 60
JS_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx", ".vue")


def _lint_error(message: str) -> str:
    """统一的失败返回（JSON 字符串）"""
    return json.dumps({_KEY_TOOL: _TOOL_NAME, "error": message}, ensure_ascii=False)


def _result(checker: str, target: str, status: str, **extra: object) -> str:
    """构造统一格式的结果 JSON"""
    payload: dict[str, object] = {
        _KEY_TOOL: _TOOL_NAME,
        _KEY_CHECKER: checker,
        _KEY_TARGET: target,
        _KEY_STATUS: status,
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


async def _run_cmd(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    """执行外部命令，返回 (returncode, stdout, stderr)

    超时或命令不存在时返回 returncode=-1，由调用方决定如何呈现。
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        return -1, "", "命令执行超时"
    except OSError as e:
        return -1, "", f"命令无法执行: {e}"
    return (
        proc.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


@tool(
    name="run_linter",
    category="review",
    timeout=60,
    description="""对指定文件或目录运行代码规范检查（ruff/eslint/architecture）。
支持 Python (.py) → ruff 检查 + 自动修复
支持 JS/TS/Vue (.js/.ts/.vue) → eslint 检查
支持全项目架构检查 ("architecture") → architecture_check.py

返回 JSON 格式的错误列表，每条包含: file, line, severity, message

此工具应在修改代码后自动调用，让 LLM 根据检查结果修复代码。
""",
)
class LintTool:
    """代码规范检查工具 — 支持 ruff / eslint / architecture_check"""

    async def __call__(self, target: str = ".", fix: bool = True) -> str:
        """执行代码规范检查

        Args:
            target: 文件路径、目录路径、或 "architecture"（全项目架构检查）
            fix: 是否自动修复可修复的问题（ruff --fix）

        Returns:
            JSON 格式的检查结果
        """
        try:
            if target in ("architecture", "arch"):
                return await self._run_architecture_check()

            target_path = Path(target)
            if not target_path.is_absolute():
                target_path = ROOT / target_path

            ext = target_path.suffix.lower()
            if ext == ".py":
                result = await self._run_ruff(target_path, fix)
            elif ext in JS_EXTENSIONS:
                result = await self._run_eslint(target_path)
            elif target_path.is_dir():
                result = await self._run_dir(target, target_path, fix)
            else:
                result = _lint_error(
                    f"不支持的文件类型: {ext}，支持 .py / .js / .ts / .vue / 'architecture'"
                )
        except Exception as e:
            return _lint_error(f"检查执行失败: {e}")
        return result

    async def _run_dir(self, target: str, target_path: Path, fix: bool) -> str:
        """目录检查：自动识别目录内包含的文件类型"""
        try:
            py_files = list(target_path.rglob("*.py"))
            js_files = [f for f in target_path.rglob("*") if f.suffix in JS_EXTENSIONS]
            results = []
            if py_files:
                results.append(await self._run_ruff(target_path, fix))
            if js_files:
                results.append(await self._run_eslint(target_path))
        except Exception as e:
            return _lint_error(f"目录检查失败: {e}")

        if not results:
            return _lint_error(f"目标 {target} 中没有可检查的文件")
        return "\n---\n".join(results)

    # ── ruff ──

    async def _run_ruff(self, target: Path, fix: bool) -> str:
        """运行 ruff check"""
        cmd = [
            _CHECKER_RUFF,
            "check",
            str(target),
            "--config",
            str(ROOT / "flypig" / "pyproject.toml"),
        ]
        if fix:
            cmd.append("--fix")

        try:
            code, out, err = await _run_cmd(cmd, ROOT, _RUFF_TIMEOUT)
        except Exception as e:
            return _lint_error(f"ruff 执行失败: {e}")

        if code == 0:
            return _result(
                _CHECKER_RUFF,
                str(target),
                _STATUS_PASSED,
                fixed=fix,
                detail=out.strip() or "无问题",
                errors=[],
            )

        errors = parse_ruff_output(out)
        return _result(
            _CHECKER_RUFF,
            str(target),
            _STATUS_FAILED,
            fixed=fix,
            error_count=len(errors),
            errors=errors,
            stderr=err.strip() or "",
        )

    # ── eslint ──

    async def _run_eslint(self, target: Path) -> str:
        """运行 eslint 检查"""
        vue_dir = ROOT / "flypig" / "interface" / "web" / "static_vite"
        cmd = [
            "npx",
            _CHECKER_ESLINT,
            str(target.relative_to(ROOT) if target.is_absolute() else target),
        ]

        try:
            code, out, err = await _run_cmd(cmd, vue_dir, _ESLINT_TIMEOUT)
        except Exception as e:
            return _lint_error(f"eslint 执行失败: {e}")

        if code == 0:
            return _result(_CHECKER_ESLINT, str(target), _STATUS_PASSED, errors=[])

        errors = parse_eslint_output(out)
        return _result(
            _CHECKER_ESLINT,
            str(target),
            _STATUS_FAILED,
            error_count=len(errors),
            errors=errors,
            stderr=err.strip() or "",
        )

    # ── architecture_check ──

    async def _run_architecture_check(self) -> str:
        """运行全项目架构检查"""
        try:
            _code, out, err = await _run_cmd(
                ["python", str(ROOT / "scripts" / "architecture_check.py")],
                ROOT,
                _ARCH_TIMEOUT,
            )
        except Exception as e:
            return _lint_error(f"architecture_check 执行失败: {e}")

        passed = "[PASS]" in out and "[FAIL]" not in out
        return _result(
            _CHECKER_ARCH,
            "architecture",
            _STATUS_PASSED if passed else _STATUS_FAILED,
            detail=out.strip(),
            stderr=err.strip() or "",
        )


__all__ = ["LintTool"]
