"""向量检索接口 (P2 预留)

为什么做：代码语义相似度检索需要向量化存储和查询，实现更智能的代码搜索。
实现方法：IVectorStore ABC 定义 embed/search 方法，sentence-transformers + SQLite 实现。
实现效果：AI 能基于语义而非关键词找到相关代码片段。
技术栈：IVectorStore ABC

层&依赖：domain.interfaces 层，零依赖
细节见文档：docs/docs_refactor/tech-stack.md → §向量检索
"""