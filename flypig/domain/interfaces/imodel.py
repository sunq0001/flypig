"""LLM 模型适配接口

为什么做：不同 LLM API（DeepSeek/Claude/GPT、国产模型）的调用方式不同，需要统一接口屏蔽差异。
实现方法：IModel ABC 定义 stream + context 两个核心方法，各模型适配器分别实现（OpenAI 兼容 / Anthropic SDK / Ollama）。
实现效果：改模型只需换适配器，对话编排代码不变。国产模型（DeepSeek/Qwen/GLM）均走 OpenAI 兼容路径。
技术栈：IModel ABC, stream, context 管理

层&依赖：domain.interfaces 层，依赖 domain/models/message.py（Message 数据类）
细节见文档：docs/docs_refactor/backend-modules.md → §模型适配、langgraph-graph.md → §chat 节点
"""