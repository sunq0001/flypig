"""LSP 诊断检查

为什么做：AI 改完代码后需要自动检查是否有语法/类型错误，不让用户看到坏了的代码。
实现方法：pyright CLI 模式检查 Python 代码，实现 ILspDiagnostics 接口。返回诊断列表（行号/级别/消息）。
实现效果：AI 改完代码后自检语法错误，可触发修复路径。
技术栈：pyright CLI, 实现 ILspDiagnostics

层&依赖：infrastructure.search 层，实现 ILspDiagnostics 接口
细节见文档：docs/docs_refactor/tech-stack.md → §LSP 诊断
"""

# TODO: 骨架文件占位，待具体实现
