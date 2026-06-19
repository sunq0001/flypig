"""模型价格获取 + 缓存

为什么做：不同模型（DeepSeek/Claude/GPT）的定价不同且会有变动，需要一个价格缓存和更新机制。
实现方法：PricingFetcher 从配置或 API 获取模型价格，写入 model_pricing 表缓存。
实现效果：用量计算使用最新的价格数据，用户看到的花费是准确的。
技术栈：PricingFetcher, 模型价格快照→model_pricing 表

层&依赖：infrastructure.usage 层，依赖 SQLAlchemy + httpx
细节见文档：docs/docs_refactor/mem_convStore_usage.md → §模型定价
"""
