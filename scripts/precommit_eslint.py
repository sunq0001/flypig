"""Pre-commit hook: 运行前端 ESLint

为什么做：pre-commit 的 mirrors-eslint 钩子在 eslint 9 + 前端 package.json
         （"type": "module"）下会尝试以 ESM 方式 import legacy `.eslintrc.json`，
         直接抛 ERR_IMPORT_ATTRIBUTE_MISSING，导致任何前端改动都无法提交。
实现方法：调用项目本地的 eslint（node node_modules/eslint/bin/eslint.js），
         并显式设置 ESLINT_USE_FLAT_CONFIG=false 走 legacy 配置加载。
层&依赖：scripts 层（QA 工具），依赖前端 node_modules 中的 eslint
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "flypig" / "interface" / "web" / "static_vite"
ESLINT_BIN = FRONTEND / "node_modules" / "eslint" / "bin" / "eslint.js"

# 仓库使用 legacy .eslintrc.json，需要显式关闭 flat config
_ENV_FLAT_CONFIG_OFF = "false"


def main() -> int:
    """执行 eslint，返回进程退出码（0 表示无 error）"""
    if not ESLINT_BIN.exists():
        print("未找到本地 eslint（node_modules 缺失），跳过前端 lint")
        return 0

    env = dict(os.environ, ESLINT_USE_FLAT_CONFIG=_ENV_FLAT_CONFIG_OFF)
    result = subprocess.run(
        ["node", str(ESLINT_BIN), "--config", ".eslintrc.json", "src/"],
        cwd=str(FRONTEND),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.stdout.strip():
        print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        print("ESLint 检查未通过，请修复后再提交。")
        return result.returncode

    print("ESLint 检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
