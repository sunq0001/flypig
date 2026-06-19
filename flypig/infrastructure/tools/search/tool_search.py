"""grep + find_files 搜索工具

为什么做：AI 需要在工作区中搜索文件内容和文件名，需要一个 fast 的搜索工具。
实现方法：subprocess grep 搜索文件内容 + Path.rglob 搜索文件名，支持正则和 glob。
实现效果：AI 快速找到需要读的文件，不需要逐目录浏览。
技术栈：subprocess grep, Path.rglob, 文件内容/结构搜索

层&依赖：infrastructure.tools.search 层，零依赖
细节见文档：docs/docs_refactor/tech-stack.md → §代码检索
"""
