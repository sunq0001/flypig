"""代码规范自动检查工具

为什么做：AI 改完代码后需要自动检查是否符合代码规范（PEP8/ruff），不让用户收到格式问题的反馈。
实现方法：subprocess 调用 ruff --fix，自动修复可修复的规范问题，返回检查结果。
实现效果：AI 输出的代码自动符合规范，用户不需要手动格式化。
技术栈：subprocess ruff --fix, 自动修复

层&依赖：infrastructure.tools.review 层，依赖 subprocess
细节见文档：docs/docs_refactor/tech-stack.md → §代码规范检查
"""