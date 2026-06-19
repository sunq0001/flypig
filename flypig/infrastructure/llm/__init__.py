"""LLM 模型适配包

为什么做：不同 LLM API（DeepSeek/Claude/GPT/本地模型）的调用方式不同，需要统一适配。
实现方法：OpenAI 兼容适配 / Anthropic SDK / Ollama 本地模型，各实现 IModel 接口。
实现效果：换模型只需改 container.py 中的绑定，不需要改任何业务代码。
技术栈：OpenAI SDK, Anthropic SDK, Ollama SDK

层&依赖：infrastructure.llm 层，实现 domain/interfaces/imodel.py
细节见文档：docs/docs_refactor/backend-modules.md → §模型适配
"""