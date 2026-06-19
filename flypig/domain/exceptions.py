"""统一异常体系

为什么做：不同模块（domain/infrastructure/backend）抛出的异常需要统一类型，上层才能统一捕获和展示，不能到处 raise Exception。
实现方法：BaseAppException 基类 → 按层派生 DomainError / InfraError / ConfigError / NotFoundError / PermissionDeniedError。
实现效果：异常链路清晰，前端可识别异常类型并展示对应的 UI（错误弹窗/权限提示/重试按钮）。
技术栈：BaseAppException → DomainError/InfraError/ConfigError

层&依赖：domain 层（零依赖），纯 Python 异常类
细节见文档：docs/docs_refactor/backend-modules.md → §异常
"""
