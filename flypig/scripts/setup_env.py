"""跨平台环境初始化脚本

为什么做：首次使用需要自动检测平台、安装依赖、创建配置文件、初始化数据库。
实现方法：Python 脚本检测操作系统 → pip install 依赖 → 复制 .env.example → 创建 conversations.db。
实现效果：用户 run 一次脚本，环境就绪。
技术栈：Python, 检测平台 + pip install + 配置文件

层&依赖：scripts 层，依赖 subprocess + 标准库
细节见文档：docs/docs_refactor/operations.md → §阶段式演进
"""