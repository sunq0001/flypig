"""安全数学计算工具

为什么做：AI 执行数学运算时不能依赖 bash eval（安全风险），需要一个安全的计算入口。
实现方法：ast.literal_eval + Decimal 进行安全数学计算。~15 行。
实现效果：AI 执行数学计算不触发代码注入，结果精确（Decimal 避免浮点精度问题）。
技术栈：ast.literal_eval + Decimal, ~15 行

层&依赖：infrastructure.tools.system 层，依赖标准库
细节见文档：docs/docs_refactor/tech-stack.md → §安全计算
"""
