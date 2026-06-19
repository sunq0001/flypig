"""Dependency Injector 容器

为什么做：所有依赖（模型、工具、存储、服务）需要统一注册和管理，不能手动 new 或者从全局变量获取。
实现方法：dependency-injector 声明式注册所有接口和实现（Wire 模式），按需 lazy 注入，测试时可 override 任意依赖。
实现效果：模块间完全解耦，替换实现（如 SQLite → PostgreSQL、DeepSeek → Claude）只需要改 container.py 里一行绑定。
技术栈：dependency-injector, async init, test override

层&依赖：core 层（胶水代码），导入所有 domain 接口 + infrastructure 实现 + orchestration 服务
细节见文档：docs/docs_refactor/backend-modules.md → §DI 容器、architecture-guide.md → §DI 单点装配、tech-stack.md → §DI 容器
"""
