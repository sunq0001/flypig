"""权限检查执行器

为什么做：每次文件/终端/git/test 操作前需要检查权限（allow/ask/deny），不能操作后才发现越权。
实现方法：check_permission(sub, obj, act) → allow/ask/deny，基于 Casbin 策略。越权弹 SuggestionCard。
实现效果：用户不再担心 AI 误操作敏感文件，所有越权行为都会被拦截或弹窗确认。
技术栈：file/term/git/test, check_permission(), allow/ask/deny

层&依赖：infrastructure.policies 层，依赖 casbin_setup.py + pycasbin
细节见文档：docs/docs_refactor/mode-matrix.md → §工具可用性
"""
