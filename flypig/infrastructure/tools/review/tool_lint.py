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
import re
from pathlib import Path

from flypig.infrastructure.tools.registry import tool

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # → flypig-agent/


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
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = ROOT / target_path

        # ── 全项目架构检查 ──
        if target == "architecture" or target == "arch":  # noqa: PLR1714
            return await self._run_architecture_check()

        # ── 单文件 / 目录检查 ──
        ext = target_path.suffix.lower()
        if ext == ".py":
            return await self._run_ruff(target_path, fix)
        elif ext in (".js", ".jsx", ".ts", ".tsx", ".vue"):
            return await self._run_eslint(target_path)
        elif target_path.is_dir():
            # 目录：自动识别包含的文件类型
            py_files = list(target_path.rglob("*.py"))
            js_files = [
                f
                for f in target_path.rglob("*")
                if f.suffix in (".js", ".jsx", ".ts", ".tsx", ".vue")
            ]
            results = []
            if py_files:
                results.append(await self._run_ruff(target_path, fix))
            if js_files:
                results.append(await self._run_eslint(target_path))
            if not results:
                return json.dumps(
                    {"tool": "run_linter", "error": f"目标 {target} 中没有可检查的文件"}
                )
            return "\n---\n".join(results)
        else:
            return json.dumps(
                {
                    "tool": "run_linter",
                    "error": f"不支持的文件类型: {ext}，支持 .py / .js / .ts / .vue / 'architecture'",
                }
            )

    # ── ruff ──

    async def _run_ruff(self, target: Path, fix: bool) -> str:
        """运行 ruff check"""
        cmd = [
            "ruff",
            "check",
            str(target),
            "--config",
            str(ROOT / "flypig" / "pyproject.toml"),
        ]
        if fix:
            cmd.append("--fix")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(ROOT),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")

        if proc.returncode == 0:
            return json.dumps(
                {
                    "tool": "run_linter",
                    "checker": "ruff",
                    "target": str(target),
                    "status": "passed",
                    "fixed": fix,
                    "detail": out.strip() or "无问题",
                    "errors": [],
                },
                ensure_ascii=False,
            )

        errors = self._parse_ruff_output(out)
        return json.dumps(
            {
                "tool": "run_linter",
                "checker": "ruff",
                "target": str(target),
                "status": "failed",
                "fixed": fix,
                "error_count": len(errors),
                "errors": errors,
                "stderr": err.strip() or "",
            },
            ensure_ascii=False,
        )

    def _parse_ruff_output(self, output: str) -> list[dict]:
        """解析 ruff check 输出为结构化错误列表"""
        errors = []
        # ruff 输出格式: path:line:col: code message
        for line in output.split("\n"):
            line = line.strip()  # noqa: PLW2901
            m = re.match(
                r"^(.+?):(\d+):(\d+):\s*(\S+)\s+(.+)",
                line,
            )
            if m:
                errors.append(
                    {
                        "file": m.group(1),
                        "line": int(m.group(2)),
                        "col": int(m.group(3)),
                        "code": m.group(4),
                        "message": m.group(5).rstrip(" *"),
                    }
                )
        return errors

    # ── eslint ──

    async def _run_eslint(self, target: Path) -> str:
        """运行 eslint 检查"""
        vue_dir = ROOT / "flypig" / "interface" / "web" / "static_vite"
        cmd = ["npx", "eslint", str(target.relative_to(ROOT) if target.is_absolute() else target)]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(vue_dir),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")

        if proc.returncode == 0:
            return json.dumps(
                {
                    "tool": "run_linter",
                    "checker": "eslint",
                    "target": str(target),
                    "status": "passed",
                    "errors": [],
                },
                ensure_ascii=False,
            )

        errors = self._parse_eslint_output(out)
        return json.dumps(
            {
                "tool": "run_linter",
                "checker": "eslint",
                "target": str(target),
                "status": "failed",
                "error_count": len(errors),
                "errors": errors,
                "stderr": err.strip() or "",
            },
            ensure_ascii=False,
        )

    def _parse_eslint_output(self, output: str) -> list[dict]:
        """解析 eslint 输出为结构化错误列表"""
        errors = []
        # eslint 紧凑格式: path:line:col: severity message [rule]
        for line in output.split("\n"):
            line = line.strip()  # noqa: PLW2901
            m = re.match(
                r"^(.+?):(\d+):(\d+):\s*(error|warning)\s+(.+?)\s+\[(.+?)\]",
                line,
            )
            if m:
                errors.append(
                    {
                        "file": m.group(1),
                        "line": int(m.group(2)),
                        "col": int(m.group(3)),
                        "severity": m.group(4),
                        "message": m.group(5),
                        "rule": m.group(6),
                    }
                )
        return errors

    # ── architecture_check ──

    async def _run_architecture_check(self) -> str:
        """运行全项目架构检查"""
        proc = await asyncio.create_subprocess_exec(
            "python",
            str(ROOT / "scripts" / "architecture_check.py"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(ROOT),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")

        passed = "[PASS]" in out and "[FAIL]" not in out
        return json.dumps(
            {
                "tool": "run_linter",
                "checker": "architecture_check",
                "status": "passed" if passed else "failed",
                "detail": out.strip(),
                "stderr": err.strip() or "",
            },
            ensure_ascii=False,
        )


__all__ = ["LintTool"]
