"""路径安全验证器

为什么做：AI 的文件操作不能越界到工作区之外的目录，需要白名单/黑名单校验。
实现方法：PathValidator 校验路径是否在允许的工作区内（白名单），检测黑名单模式（如 .git/、node_modules/），越权弹 SuggestionCard。
实现效果：AI 读写文件被限制在工作区内，敏感路径受到保护。
技术栈：白名单/黑名单/cwd 限制, 越权弹 SuggestionCard

层&依赖：infrastructure.sandbox 层，依赖 pathlib
细节见文档：docs/docs_refactor/subprocess.md → §沙箱路径验证
"""

# TODO: 骨架文件占位，待具体实现
