"""LSP 诊断接口

为什么做：改完代码后需要检查是否有语法错误/类型错误，LSP 诊断提供标准化的检查结果。
实现方法：ILspDiagnostics ABC 定义 check(file) → diagnostics[] 方法，pyright CLI 实现。
实现效果：AI 改完代码后自动检查语法错误，用户不会看到明显"坏了的代码"。
技术栈：ILspDiagnostics ABC, pyright CLI

层&依赖：domain.interfaces 层，零依赖
细节见文档：docs/docs_refactor/tech-stack.md → §LSP 诊断
"""