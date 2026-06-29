"""统一异常体系

为什么做：不同模块（domain/infrastructure/backend）抛出的异常需要统一类型，上层才能统一捕获和展示，不能到处 raise Exception。

实现方法：FlyPigException 基类 → 按场景派生 ConfigurationError / ModelAPIError / ToolExecutionError / SandboxError / CircuitBreakerError，各节点通过 safe_node 装饰器捕获并转为友好消息。

实现效果：异常链路清晰，前端可识别异常类型并展示对应的 UI（错误弹窗/权限提示/重试按钮）。

技术栈：FlyPigException → ConfigurationError/ModelAPIError/ToolExecutionError/SandboxError

层&依赖：domain 层（零依赖），纯 Python 异常类
细节见文档：docs/docs_refactor/backend-modules.md → §统一异常
"""


class FlyPigException(Exception):
    """所有 FlyPig 异常的基类"""
    pass


class ConfigurationError(FlyPigException):
    """配置错误：config.yaml 缺失字段 / API Key 未配置 / 模型名不存在"""
    pass


class ModelAPIError(FlyPigException):
    """模型 API 错误：认证失败 / 限流 / 服务不可用 / 上下文超长"""
    pass


class ToolExecutionError(FlyPigException):
    """工具执行错误：文件不存在 / 权限不足 / 执行超时"""
    pass


class SandboxError(FlyPigException):
    """沙箱错误：Docker 未运行 / 镜像拉取失败 / 沙箱超时"""
    pass


class CircuitBreakerError(FlyPigException):
    """熔断错误：连续失败超过阈值，服务暂时熔断"""
    pass

