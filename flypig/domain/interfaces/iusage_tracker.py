"""用量追踪接口

为什么做：API 调用需要记录 token/cost/cache 等用量数据，追踪方式（SQLite/云端/LangFuse）可替换。
实现方法：IUsageTracker ABC 定义 turn 级和 call 级的用量记录与查询方法，NoOp 实现可用作默认。
实现效果：所有 API 调用的费用一目了然，用户可看到每轮/每次调用的成本和缓存命中率。
技术栈：IUsageTracker ABC, turn/call 级 token/cost/cache, NoOp 可替换

层&依赖：domain.interfaces 层，依赖 domain/models 中的 UsageRecord/UsageSummary 数据类
细节见文档：docs/docs_refactor/mem_convStore_usage.md → §概述、tech-stack.md → §IUsageTracker
"""