"""共享测试配置、常量和辅助函数"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.environ["FLYPIG_TEST"] = "1"

from flypig.config import Config

cfg = Config()

# 类别常量
_FUNC = "func"
_CATEGORY_LABEL = {_FUNC: "功能测试"}
