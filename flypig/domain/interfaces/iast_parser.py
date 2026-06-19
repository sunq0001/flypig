"""AST 解析接口

为什么做：定位代码中的符号（函数/类/变量）需要 AST 解析，而不是靠正则硬搜。
实现方法：IASTParser ABC 定义 parse_symbol(symbol) → (file, line) 方法，tree-sitter 实现。
实现效果：read_file/patch_file 可以根据符号名定位到具体行号，不再依赖用户指定行数。
技术栈：IASTParser ABC, tree-sitter, symbol→行号

层&依赖：domain.interfaces 层，零依赖
细节见文档：docs/docs_refactor/tech-stack.md → §AST 解析
"""