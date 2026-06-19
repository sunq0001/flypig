"""消息/工具调用/选择题数据类

为什么做：AI 对话产生的消息（用户/AI/系统）、工具调用请求和结果、选择题选项等需要结构化数据表示。
实现方法：@dataclass 定义 Message (role/content/tool_calls)、ToolCall (id/name/args)、ChoiceCard (options/selection)。
实现效果：消息类型安全，序列化为 SSE 事件时格式统一。
技术栈：@dataclass, Message/ToolCall/ChoiceCard

层&依赖：domain.models 层，零依赖
细节见文档：docs/docs_refactor/api-reference.md → §SSE 事件格式
"""