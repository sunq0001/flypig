"""用量事件处理器

为什么做：每轮/每次 API 调用后需要自动记录用量，不能手动调用记录接口。
实现方法：订阅 tool:after 和 turn:end 事件，自动记录 token/cost/cache 用量到数据库。
实现效果：用量全自动记录，不需要业务代码关心。记录只存不处理，符合"AI suggests, user decides"原则。
技术栈：订阅 hooks, 自动记录 token/cost, 不自动处理

层&依赖：infrastructure.usage 层，依赖 IHook + IUsageTracker
细节见文档：docs/docs_refactor/mem_convStore_usage.md → §核心哲学
"""
