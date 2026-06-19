"""AST 符号→行号解析

为什么做：read_file/patch_file 需要根据符号名（函数名/类名）定位到具体行号，不能用正则硬搜。
实现方法：tree-sitter 解析代码 AST，symbol→(file, start_line, end_line) 映射，实现 IASTParser。
实现效果：AI 说"读文件 login_user 函数"就能跳到对应行，不需要复制行号。
技术栈：tree-sitter, 实现 IASTParser

层&依赖：infrastructure.search 层，实现 IASTParser 接口
细节见文档：docs/docs_refactor/tech-stack.md → §AST 解析
"""