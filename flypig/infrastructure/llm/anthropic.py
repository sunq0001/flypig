"""Claude 适配

为什么做：用户可选 Claude 作为 AI 模型后端，需要实现 IModel 接口适配 Anthropic SDK。
实现方法：Anthropic SDK 消息格式转换（turbo-json → Claude 格式），实现 IModel 的 stream + context。
实现效果：Claude 用户无需额外配置，DI 容器绑定即可。
技术栈：Anthropic SDK, 消息格式转换

层&依赖：infrastructure.llm 层，实现 IModel，依赖 anthropic
细节见文档：docs/docs_refactor/backend-modules.md → §模型适配
"""
