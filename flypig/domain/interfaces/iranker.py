"""多源排序接口 (P2 预留)

为什么做：grep/AST/向量/知识图谱的搜索结果需要融合排序，提供最佳结果。
实现方法：IRanker ABC 定义 rank(results) → sorted_results 方法。
实现效果：多源搜索结果的排序合理，用户不看遗漏。
技术栈：IRanker ABC, FlashRank

层&依赖：domain.interfaces 层，零依赖
细节见文档：docs/docs_refactor/tech-stack.md → §多源排序
"""
