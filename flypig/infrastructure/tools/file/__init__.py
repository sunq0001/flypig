"""文件操作工具包

为什么做：AI 读写文件需要安全可控的统一入口（路径校验/大小限制/二进制检测）。
实现方法：实现文件 CRUD 工具（read/write/patch/delete/list_dir），走 PathValidator 路径审批。
实现效果：AI 读写文件不会越界，大文件自动截断，二进制文件自动标记。
技术栈：aiofiles, PathValidator

层&依赖：infrastructure.tools.file 层，依赖 PathValidator（infrastructure/sandbox）
细节见文档：docs/docs_refactor/tools.md → §文件编辑方案
"""

__all__ = []
