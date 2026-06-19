"""删除文件工具

为什么做：AI 需要删除文件时必须走安全确认流程，不能直接 os.remove。
实现方法：PathValidator 校验路径 → 权限检查 → 确认弹窗 → os.remove。
实现效果：误删文件有安全兜底，用户不会无感知丢失文件。
技术栈：os.remove, 安全确认

层&依赖：infrastructure.tools.file 层，依赖 PathValidator + PolicyService
细节见文档：docs/docs_refactor/tools.md → §文件编辑方案
"""