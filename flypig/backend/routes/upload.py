"""文件上传路由 (/api/upload)

为什么做：用户可以通过前端拖拽或选择文件上传到工作区，自动解压压缩包。
实现方法：Element Plus Upload 前端上传 → 后端接收 → zipfile 自动解压。
实现效果：用户上传项目模板或代码包后直接可用，不需要手动解压。
技术栈：Element Plus Upload + 后端 zipfile, 拖拽

层&依赖：backend.routes 层，依赖 zipfile + Element Plus Upload（前端）
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""
