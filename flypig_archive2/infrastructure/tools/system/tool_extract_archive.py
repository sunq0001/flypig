"""压缩解压工具（含 Zip Slip 防护）

为什么做：AI 需要上传和解压压缩包（项目模板/移动端代码包），但 Zip Slip 攻击可能导致目录穿越。
实现方法：zipfile/tarfile/py7zr 解压，路径穿越检测（Zip Slip 防护）。
实现效果：AI 安全解压用户上传的压缩包，不会覆盖工作区外的文件。
技术栈：zipfile/tarfile/py7zr, 路径穿越检测

层&依赖：infrastructure.tools.system 层，依赖标准库
细节见文档：docs/docs_refactor/tech-stack.md → §压缩解压、tools.md → §安全
"""
