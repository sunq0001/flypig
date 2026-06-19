"""领域数据类包

为什么做：Message/Session/Task 等跨层数据需要统一的 dataclass 定义，避免到处用 dict 传参。
实现方法：@dataclass 定义每个数据类，类型提示完备，序列化/反序列化统一。
实现效果：函数签名自文档化，IDE 自动补全，类型检查器可发现错误。
技术栈：@dataclass, dataclasses

层&依赖：domain.models 层，零依赖（纯 dataclass）
细节见文档：docs/docs_refactor/backend-modules.md → §数据类型规范
"""