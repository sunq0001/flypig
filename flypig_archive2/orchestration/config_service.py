"""配置管理服务

为什么做：用户需要在前端修改配置（模型选择/API Key 等），需要一个服务层封装配置的 CRUD 和持久化。
实现方法：ConfigService 提供 Config 初始化、模型切换、API Key 管理接口，修改后序列化到 YAML 文件。~80 行。
实现效果：用户在前端改配置一键生效，不需要重启应用。
技术栈：Config 初始化/模型切换/API Key 管理, ~80 行

层&依赖：orchestration 层，依赖 domain/config（Config/ModelRegistry data class）
细节见文档：docs/docs_refactor/backend-modules.md → §ConfigService
"""
