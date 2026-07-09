"""Pre-commit hook: 在 flypig 前端目录运行 ESLint"""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
frontend = root / "flypig" / "interface" / "web" / "static_vite"

# Windows 下 npx 可能不在 PATH 中，用 shell=True 确保能找到
result = subprocess.run(  # noqa: PLW1510
    "npx eslint src/",
    cwd=str(frontend),
    capture_output=True,
    text=True,
    shell=True,
)

if result.returncode != 0:
    print(result.stdout)
    print(result.stderr)
    print("ESLint 检查未通过，请修复后再提交。")
    sys.exit(1)

print("ESLint 检查通过")
sys.exit(0)
