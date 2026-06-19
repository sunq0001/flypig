"""多源排序器 (P2)

为什么做：grep/AST/向量/知识图谱的多个搜索源返回的结果需要融合排序，提供最佳匹配结果。
实现方法：自研 ~50 行多源融合 + FlashRank（可选 LLM-free reranker），实现 IRanker。P2 启用。
实现效果：搜索结果按相关性排序，用户（和 AI）看到的第一个结果就是最相关的。
技术栈：自研 ~50 行 + FlashRank, 实现 IRanker

层&依赖：infrastructure.search 层，实现 IRanker 接口
细节见文档：docs/docs_refactor/tech-stack.md → §多源排序
"""