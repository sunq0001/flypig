"""配置路由 (/api/config/*)

为什么做：用户需要在前端查看和修改配置（模型选择/API Key），不能直接操作文件。
实现方法：Quart GET/PUT 端点，通过 ConfigService 查询/修改配置。≤80 行。
实现效果：用户在前端可视化配置，不需要手动编辑 YAML 文件。
技术栈：Quart, ConfigService, GET/PUT, ≤80 行

层&依赖：backend.routes 层，依赖 orchestration/config_service.py
细节见文档：docs/docs_refactor/api-reference.md → §REST 端点
"""