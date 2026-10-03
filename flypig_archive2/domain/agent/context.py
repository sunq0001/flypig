"""模式上下文约束

为什么做：Explore/Plan/Execute 三种模式需要不同的工具列表、温度、身份 prompt，但不能改图结构。
实现方法：根据 AgentState 中的 mode 字段，动态构造传给 LLM 的 context 约束（可用工具/温度/角色 prompt）。
实现效果：模式切换不改变图拓扑，只改变 context 约束，LLM 在约束内自行决定路径。
技术栈：Explore/Plan/Execute 工具列表/温度/身份 prompt

层&依赖：domain.agent 层，依赖 state.py + domain/prompts（角色 prompt）
细节见文档：docs/docs_refactor/mode-matrix.md → §工具可用性明细
"""
