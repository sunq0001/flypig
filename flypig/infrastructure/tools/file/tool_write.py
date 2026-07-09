"""写文件工具

为什么做：AI 需要创建新文件或全量重写已有文件，需要一个受控的写入入口。
实现方法：aiofiles 写入，写入前走 PathValidator 路径审批 + 权限检查。
实现效果：AI 写文件有审核绑定，不绕过安全策略。
技术栈：aiofiles, 写入前审批检查

层&依赖：infrastructure.tools.file 层，依赖 PathValidator + PolicyService
细节见文档：docs/docs_refactor/tools.md → §文件编辑方案
"""

# TODO: 骨架文件占位，待具体实现
