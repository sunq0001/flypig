"""review 工具包 — 代码审查/规范检查/质量门禁

为什么做：AI 写完代码后需要自动审查规范、运行 lint、检查架构，
         审查结果喂回 chat 节点让 LLM 自愈，不需要用户手动反馈 lint 错误。
实现方法：通过 @tool 装饰器注册 run_linter（支持 ruff/eslint/architecture_check），
         ToolExecutor 加载后 LLM 可直接调用。
层&依赖：infrastructure.tools.review 层，依赖 subprocess + registry + tool 装饰器
"""

from flypig.infrastructure.tools.review.tool_lint import LintTool

__all__ = ["LintTool"]
