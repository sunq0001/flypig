"""Pre-commit hook wrapper for vitest — 设置正确的 working directory.

vitest.config.js 在 flypig/interface/web/static_vite/ 下，
pre-commit 默认从 repo 根目录运行，vitest 找不到配置，导致 @ 别名失效。

此脚本负责 cd 到正确目录再调用 npx vitest。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    vite_dir = (
        Path(__file__).resolve().parent.parent
        / "flypig"
        / "interface"
        / "web"
        / "static_vite"
    )
    result = subprocess.run(
        ["npx", "vitest", "run", "--reporter=verbose"],
        cwd=str(vite_dir),
        shell=True,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
