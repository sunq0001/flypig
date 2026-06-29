"""知识图谱查询 (P1)

为什么做：代码的函数调用/类继承/模块依赖关系可以通过知识图谱可视化，比逐文本搜索更智能。
实现方法：基于 AST 关系抽取函数/类/模块关系图，实现 IKnowledgeGraph。~300 行自研。
实现效果：AI 能回答"这个函数被谁调用了""这个类继承了哪些基类"等问题。
技术栈：自研 ~300 行 AST 关系抽取, 实现 IKnowledgeGraph

层&依赖：infrastructure.search 层，实现 IKnowledgeGraph 接口
细节见文档：docs/docs_refactor/tech-stack.md → §知识图谱
"""
