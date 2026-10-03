"""grep 全文搜索 (MVP)

为什么做：MVP 阶段需要快速实现代码搜索，grep + Path.rglob 零依赖，够用。
实现方法：subprocess grep 搜索文件内容 + Path.rglob 搜索文件名，实现 ISearch 接口。
实现效果：AI 可以在对话中搜索代码中的关键字/函数名/类名。
技术栈：subprocess grep, Path.rglob, 实现 ISearch

层&依赖：infrastructure.search 层，实现 ISearch 接口（domain/interfaces/isearch.py）
细节见文档：docs/docs_refactor/tech-stack.md → §代码检索
"""

# TODO: 骨架文件占位，待具体实现
