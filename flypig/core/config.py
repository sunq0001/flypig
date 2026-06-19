"""应用配置加载

为什么做：配置（模型选择、API Key、项目路径等）散落在环境变量、YAML 文件、命令行参数中，需要一个统一的加载入口。
实现方法：pydantic-settings 从环境变量加载，PyYAML 从 config.yaml 加载，按 env var > YAML > 默认值 优先级覆盖。
实现效果：改一个配置文件或环境变量即可控制全局行为，不用翻代码改常量。
技术栈：pydantic-settings, PyYAML, python-dotenv, dataclasses

层&依赖：core 层（无业务依赖），纯配置加载，不依赖任何模块
细节见文档：docs/docs_refactor/backend-modules.md → §配置即代码、tech-stack.md → §配置
"""
