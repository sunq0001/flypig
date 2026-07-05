"""统一异常体系（含 error code）

为什么做：不同模块抛出的异常需要统一类型 + 错误码，上层才能统一捕获、展示和国际化。

实现方法：FlyPigException(code, message, details) 基类 → 各场景派生，每个异常携带 code 字符串。

实现效果：异常链路清晰，前端根据 code 做 i18n，不依赖 exception message 做判断。

层&依赖：domain 层（零依赖）
"""


class FlyPigException(Exception):
    """所有 FlyPig 异常的基类"""

    code: str = "UNKNOWN"

    def __init__(self, message: str = "", details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": self.details}


# ── Domain Error ──────────────────────────────────────────────────


class DomainError(FlyPigException):
    """领域层业务规则冲突"""

    code = "DOMAIN_ERR"


class SessionClosedError(DomainError):
    """会话已关闭，不能继续发送消息"""

    code = "SESSION_CLOSED"


class InvalidTurnError(DomainError):
    """非法轮次跃迁"""

    code = "INVALID_TURN"


class MessageValidationError(DomainError):
    """消息内容不合法"""

    code = "MSG_INVALID"


# ── Configuration ─────────────────────────────────────────────────


class ConfigurationError(FlyPigException):
    """配置错误：config.yaml 缺失字段 / API Key 未配置 / 模型名不存在"""

    code = "CONFIG_ERROR"


# ── Model API ─────────────────────────────────────────────────────


class ModelAPIError(FlyPigException):
    """模型 API 错误：认证失败 / 限流 / 服务不可用 / 上下文超长"""

    code = "MODEL_API_ERR"


class CircuitBreakerError(FlyPigException):
    """熔断错误：连续失败超过阈值，服务暂时熔断"""

    code = "CIRCUIT_OPEN"


# ── Tool Execution ────────────────────────────────────────────────


class ToolExecutionError(FlyPigException):
    """工具执行错误：文件不存在 / 权限不足 / 执行超时"""

    code = "TOOL_EXEC_ERR"


# ── Sandbox ───────────────────────────────────────────────────────


class SandboxError(FlyPigException):
    """沙箱错误：Docker 未运行 / 镜像拉取失败 / 沙箱超时"""

    code = "SANDBOX_ERR"
