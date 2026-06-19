"""FlyPig 编排层

为什么做：AI 对话的流程控制（LangGraph 图构建、对话调度、配置管理、会话管理、权限控制、事件订阅、checkpoint、上下文压缩、建议生成、用量追踪）需要统一的服务层封装。
实现方法：orchestration 包提供所有编排服务（ChatService/ConfigService/SessionService/PolicyService/GraphFactory 等），通过 core/container.py 注册到 DI 容器。
实现效果：服务职责单一可独立测试，编排逻辑不散落在后端路由中。
技术栈：LangGraph, SQLAlchemy, Casbin, GitPython

层&依赖：orchestration 层，依赖 domain 接口 + infrastructure 实现
细节见文档：docs/docs_refactor/backend-modules.md → §Orchestration Layer
"""
