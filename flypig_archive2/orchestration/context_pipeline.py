"""上下文压缩管线

为什么做：长对话超出模型 token 窗口时需要压缩上下文，但不能直接丢弃所有早期对话。
实现方法：CompositePipeline 按层顺序压缩（TruncateResultsLayer → FoldOldTurnsLayer → TrimMessagesLayer），每层减少一定 token。
实现效果：对话越长越不会超窗口，早期的关键信息不会被完全丢。
技术栈：CompositePipeline, Truncate+Fold+Trim 三层, SQLAlchemy 读取

层&依赖：orchestration 层，依赖 IConversationStore（读取原始对话）+ IContextPipeline 接口
细节见文档：docs/docs_refactor/short-term-memory.md → §职责、§内置三层
"""
