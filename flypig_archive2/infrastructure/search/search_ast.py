"""AST 代码搜索 (P1)

为什么做：grep 只做文本匹配，无法理解代码结构（函数定义/类继承/调用关系）。AST 搜索按结构匹配。
实现方法：tree-sitter / ast-grep 进行结构化代码搜索，实现 ISearch 接口。P1 启用。
实现效果：AI 能根据代码结构（如"所有继承 BaseModel 的类"）找到相关的代码。
技术栈：tree-sitter / ast-grep, 结构匹配

层&依赖：infrastructure.search 层，实现 ISearch 接口
细节见文档：docs/docs_refactor/tech-stack.md → §结构化代码搜索
"""
