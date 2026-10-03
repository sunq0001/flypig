"""lint_parser — ruff / eslint 输出解析

为什么做：tool_lint.py 同时承担「执行检查器」与「解析输出」两件事，文件过长；
         把纯字符串解析抽成独立模块，便于单测且让执行流程保持简洁。
实现方法：用带具名分组的正则把 ruff / eslint 紧凑输出解析为结构化 dict 列表。
层&依赖：infrastructure.tools.review 层，仅依赖 re
"""

from __future__ import annotations

import re

# ── 错误条目的字段名（同时用作正则具名分组名）──
FIELD_FILE = "file"
FIELD_LINE = "line"
FIELD_COL = "col"
FIELD_CODE = "code"
FIELD_SEVERITY = "severity"
FIELD_MESSAGE = "message"
FIELD_RULE = "rule"

_RUFF_LINE_RE = re.compile(
    rf"^(?P<{FIELD_FILE}>.+?):(?P<{FIELD_LINE}>\d+):(?P<{FIELD_COL}>\d+):"
    rf"\s*(?P<{FIELD_CODE}>\S+)\s+(?P<{FIELD_MESSAGE}>.+)"
)
_ESLINT_LINE_RE = re.compile(
    rf"^(?P<{FIELD_FILE}>.+?):(?P<{FIELD_LINE}>\d+):(?P<{FIELD_COL}>\d+):"
    rf"\s*(?P<{FIELD_SEVERITY}>error|warning)\s+(?P<{FIELD_MESSAGE}>.+?)"
    rf"\s+\[(?P<{FIELD_RULE}>.+?)\]"
)


def parse_ruff_output(output: str) -> list[dict]:
    """解析 ruff check 输出（格式：path:line:col: code message）"""
    errors = []
    for line in output.split("\n"):
        m = _RUFF_LINE_RE.match(line.strip())
        if m:
            errors.append(
                {
                    FIELD_FILE: m.group(FIELD_FILE),
                    FIELD_LINE: int(m.group(FIELD_LINE)),
                    FIELD_COL: int(m.group(FIELD_COL)),
                    FIELD_CODE: m.group(FIELD_CODE),
                    FIELD_MESSAGE: m.group(FIELD_MESSAGE).rstrip(" *"),
                }
            )
    return errors


def parse_eslint_output(output: str) -> list[dict]:
    """解析 eslint 紧凑输出（格式：path:line:col: severity message [rule]）"""
    errors = []
    for line in output.split("\n"):
        m = _ESLINT_LINE_RE.match(line.strip())
        if m:
            errors.append(
                {
                    FIELD_FILE: m.group(FIELD_FILE),
                    FIELD_LINE: int(m.group(FIELD_LINE)),
                    FIELD_COL: int(m.group(FIELD_COL)),
                    FIELD_SEVERITY: m.group(FIELD_SEVERITY),
                    FIELD_MESSAGE: m.group(FIELD_MESSAGE),
                    FIELD_RULE: m.group(FIELD_RULE),
                }
            )
    return errors


__all__ = ["parse_eslint_output", "parse_ruff_output"]
