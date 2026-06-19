"""Dockerfile 生成 + 镜像构建

为什么做：AI 需要在沙箱内安装依赖时，可能需要定制化的镜像，不能每次都从零拉大镜像。
实现方法：根据项目需求动态生成 Dockerfile → Docker SDK build 镜像。
实现效果：沙箱镜像按需构建，构建结果可缓存复用。
技术栈：Docker SDK build

层&依赖：infrastructure.sandbox 层，依赖 Docker SDK
细节见文档：docs/docs_refactor/subprocess.md → §沙箱配置
"""