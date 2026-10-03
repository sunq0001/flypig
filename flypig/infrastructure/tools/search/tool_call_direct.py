"""懒加载直接调用工具

为什么做：AI 知道工具名但不在当前工具列表中时，需要按名直接调工具。
实现方法：按工具名查找已注册工具，直接执行并返回结果。
实现效果：AI 跨模式调用工具更加灵活，不需要模式切换。
技术栈：按名直接调工具

层&依赖：infrastructure.tools.search 层，依赖 ToolExecutor 注册表
细节见文档：docs/docs_refactor/tools.md → §工具注册
"""

# TODO: 骨架文件占位，待具体实现
