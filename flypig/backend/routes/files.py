"""文件操作路由 (/api/files /api/file /api/tree)

为什么做：前端文件树和编辑器需要通过 API 读取文件内容和目录树。
实现方法：Quart GET 端点，通过文件系统读取工作区内容和目录结构。≤80 行。
实现效果：前端文件树自动展开/刷新，编辑器实时加载文件内容。
技术栈：Quart, read/write/tree, ≤80 行

层&依赖：backend.routes 层，依赖 PathValidator + 本地文件系统
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""
