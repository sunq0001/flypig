"""向量语义检索 (P2)

为什么做：基于关键词的搜索无法理解语义（如搜"登录"找不到 login），向量检索按语义相似度匹配。
实现方法：sentence-transformers 生成嵌入 + SQLite 存储，实现 IVectorStore。P2 启用。
实现效果：AI 能根据语义找到相关代码，不依赖关键词精确匹配。
技术栈：sentence-transformers + SQLite, 实现 IVectorStore

层&依赖：infrastructure.search 层，实现 IVectorStore 接口
细节见文档：docs/docs_refactor/tech-stack.md → §向量检索
"""