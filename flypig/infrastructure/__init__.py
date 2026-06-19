"""FlyPig 基础设施层

为什么做：LLM 适配、工具执行、沙箱、用量追踪、搜索、权限——这些"怎么做"的实现需要与"做什么"的领域层分离。
实现方法：infrastructure 层实现 domain/interfaces 中定义的所有接口，包括 LLM 适配 / 工具 / 沙箱 / 用量 / 搜索 / 权限。
实现效果：替换实现（如换模型/换搜索方式）不需要改业务代码，领域层零感知。
技术栈：OpenAI SDK, Docker SDK, SQLAlchemy, Loguru, subprocess, GitPython, Ruff

层&依赖：infrastructure 层（最外层），实现 domain 接口，依赖第三方库
细节见文档：docs/docs_refactor/backend-modules.md → §Infrastructure Layer
"""