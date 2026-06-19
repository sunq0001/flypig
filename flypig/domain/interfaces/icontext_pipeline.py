"""上下文压缩接口

为什么做：长对话的上下文超出模型窗口时，需要在调用 LLM 前压缩。压缩策略可替换（截断/折叠/摘要）。
实现方法：IContextPipeline ABC 定义 build() + compress() 方法，CompositePipeline 按层组合（Truncate→Fold→Trim）。
实现效果：对话越长越不会超窗口，用户体验不掉。压缩策略可插拔，不影响对话逻辑。
技术栈：IContextPipeline ABC, budget 预算, CompositePipeline

层&依赖：domain.interfaces 层，依赖 IConversationStore（读取对话原始数据）
细节见文档：docs/docs_refactor/short-term-memory.md → §接口、§内置三层
"""