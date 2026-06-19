"""MultiRoleManager

为什么做：AI 在不同阶段（分析需求/审查代码/测试用例/评估架构）需要不同的角色 prompt，需要一个管理器按需切换。
实现方法：MultiRoleManager 根据当前 mode + 节点名，从 roles/ 目录加载对应的 .md prompt 文件并组装为系统消息。
实现效果：prompt 与代码分离，无需改代码即可调整 AI 的行为角色。~50 行自研实现。
技术栈：MultiRoleManager, 按角色+模型+会话维度选 prompt, ~50 行自研

层&依赖：domain.prompts 层，依赖 roles/*.md 文件
细节见文档：docs/docs_refactor/tech-stack.md → §MultiRoleManager
"""
