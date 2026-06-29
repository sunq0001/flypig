"""知识图谱接口 (P1 预留)

为什么做：代码的关系网络（函数调用、模块依赖、类继承）可以通过知识图谱可视化查询。
实现方法：IKnowledgeGraph ABC 定义 query_related/query_dependencies 方法。
实现效果：AI 可以理解代码间的深层关系，不只是逐文件搜索。
技术栈：IKnowledgeGraph ABC

层&依赖：domain.interfaces 层，零依赖
细节见文档：docs/docs_refactor/tech-stack.md → §知识图谱
"""
