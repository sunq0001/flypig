"""OpenAI/DeepSeek 兼容适配

为什么做：DeepSeek/Qwen/GLM 等国产模型均兼容 OpenAI API 格式，一个适配器可覆盖多数模型。
实现方法：OpenAI SDK stream=True，封装为 IModel 接口的 stream + context 方法。兼容 base_url 配置。
实现效果：切换国产模型只需改 base_url 和 model_name，代码不变。
技术栈：OpenAI SDK, stream=True, context 管理

层&依赖：infrastructure.llm 层，实现 IModel，依赖 openai
细节见文档：docs/docs_refactor/backend-modules.md → §模型适配、tech-stack.md → §AI 模型 SDK
"""
