"""Prompt 管理系统

为什么做：不同角色（开发者/审查者/测试者）需要不同的系统提示词，不能硬编码在节点函数中。
实现方法：导出 MultiRoleManager，按角色加载 roles/ 下的 .md prompt 文件。
实现效果：换角色 prompt 只需改 roles/ 下的 .md 文件，不需要改 Python 代码。
技术栈：MultiRoleManager, 角色 prompt 库

层&依赖：domain.prompts 层，依赖 domain/config（模型配置）
细节见文档：docs/docs_refactor/tech-stack.md → §MultiRoleManager

使用方式：from domain.prompts import MultiRoleManager
"""

from .multirole_manager import MultiRoleManager
