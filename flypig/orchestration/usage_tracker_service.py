"""用量追踪编排

为什么做：每轮 AI 对话的 token/cost/cache 用量需要自动记录，用户可查询历史用量和花费。
实现方法：UsageTrackerService 组合 IUsageTracker + PricingFetcher，通过 EventSubscriptions 自动订阅 tool:after 事件记录用量。~60 行。
实现效果：用户在前端可以看到每轮对话的 token 数、缓存命中率和花费。
技术栈：IUsageTracker + PricingFetcher, EventSubscriptions 自动记录, ~60 行

层&依赖：orchestration 层，依赖 IUsageTracker + PricingFetcher（infrastructure/usage）
细节见文档：docs/docs_refactor/mem_convStore_usage.md → §数据模型、backend-modules.md → §UsageTrackerService
"""