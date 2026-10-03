"""安全文件读取工具

为什么做：AI 读文件时不能裸读磁盘，没有边界保护的话恶意链接或超大文件会拖垮体验。
实现方法：PathValidator 白名单校验 → 按上限截断大文件 → magic bytes 检测二进制。支持 start/end 范围和 symbol 符号定位。
实现效果：读到恶意路径时弹出 SuggestionCard 让用户选择；大文件不会卡死 UI；二进制文件直接标出。
技术栈：aiofiles, start/end 范围, symbol 符号定位, magic bytes 检测

层&依赖：infrastructure.tools.file 层，依赖 PathValidator
细节见文档：docs/docs_refactor/tools.md → §文件编辑方案
"""
