"""本地模型适配 (预留)

为什么做：用户可选本地部署的 Ollama/vLLM 作为模型后端，无需 API Key。
实现方法：Ollama/vLLM 兼容接口，实现 IModel 的 stream 方法。预留扩展点。
实现效果：离线场景下可用本地模型替代云端 API。
技术栈：Ollama/vLLM 兼容接口

层&依赖：infrastructure.llm 层，实现 IModel
细节见文档：docs/docs_refactor/backend-modules.md → §模型适配
"""

# TODO: 骨架文件占位，待具体实现
