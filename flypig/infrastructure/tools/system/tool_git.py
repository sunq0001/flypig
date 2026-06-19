"""Git 操作封装工具

为什么做：AI 执行 git 操作时如果用裸 bash git 不可控（输出解析困难、错误处理复杂），需要结构化的 git 工具。
实现方法：GitPython 薄封装，status/diff/log/commit/branch 返回结构化数据（dict），非裸字符串。
实现效果：AI 可以获知 git status/diff/log 的结构化结果，可靠执行 add/commit 等操作。
技术栈：GitPython, status/diff/log/commit/branch 结构化返回

层&依赖：infrastructure.tools.system 层，依赖 GitPython
细节见文档：docs/docs_refactor/tech-stack.md → §Git 操作、tools.md → §回滚
"""