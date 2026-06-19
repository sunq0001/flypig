"""列出目录工具

为什么做：AI 需要了解工作区的文件和目录结构才能规划修改路径。
实现方法：Path.rglob 递归遍历，collections.Counter 统计语言分布。deep=False 只列一层，deep=True 递归+语言统计。
实现效果：AI 能快速了解项目结构，不需要逐层遍历目录。
技术栈：Path.rglob, collections.Counter, deep/浅层

层&依赖：infrastructure.tools.file 层，依赖 PathValidator
细节见文档：docs/docs_refactor/tools.md → §文件编辑方案、tech-stack.md → §项目扫描
"""