"""Config dataclass

为什么做：项目配置（模型选择/API Key/工作区路径等）需要一个类型安全的结构体，避免 stringly-typed。
实现方法：@dataclass 定义 Config（project/model/mode/apikey 等字段），通过 core/config.py 的加载器填充。
实现效果：所有模块通过 Config 实例获取配置，不需要到处读环境变量。
技术栈：@dataclass, 项目/模型/模式/API Key 配置

层&依赖：domain.config 层，零依赖
细节见文档：docs/docs_refactor/backend-modules.md → §配置即代码
"""