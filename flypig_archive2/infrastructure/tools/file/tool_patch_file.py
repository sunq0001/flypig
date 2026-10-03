"""局部更新工具

为什么做：AI 经常需要修改文件中的某几行而不是全量重写，简单的 old_str→new_str 替换在复杂场景下极易出错。
实现方法：使用 Aider 编辑引擎（推荐）或 unified diff + git apply（轻量），按 anchor 定位修改，多匹配时自动回退。
实现效果：复杂编辑场景下修改准确率高，不会因缩进/空格差异导致替换失败。
技术栈：Aider 编辑引擎 / git apply, anchor 定位, 回退策略

层&依赖：infrastructure.tools.file 层，依赖 GitPython + subprocess
细节见文档：docs/docs_refactor/tools.md → §文件编辑方案
"""
