"""模式枚举 + 配置

为什么做：Explore/Plan/Execute 三种模式需要枚举定义和对应的配置信息（温度/工具集/身份）。
实现方法：ExecutionMode Enum + ModeConfig dataclass（温度范围/可用工具列表/默认 prompt 身份）。
实现效果：模式切换通过修改 ModeConfig 实现，而不是通过 if-else 分支。
技术栈：ExecutionMode enum, ModeConfig

层&依赖：domain.models 层，零依赖
细节见文档：docs/docs_refactor/mode-matrix.md → §核心矩阵
"""
