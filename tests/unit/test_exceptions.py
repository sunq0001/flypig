"""
test_exceptions

为何做：测试 domain/exceptions.py 统一异常体系的所有异常类

如何测：
- FlyPigException 基类的 code/message/details 属性
- to_dict() 序列化输出
- 各子类继承的默认 code

层&依赖：tests.unit 层，依赖 domain.exceptions
"""

from flypig.domain.exceptions import (
    CircuitBreakerError,
    ConfigurationError,
    DomainError,
    FlyPigException,
    InvalidTurnError,
    MessageValidationError,
    ModelAPIError,
    SandboxError,
    SessionClosedError,
    ToolExecutionError,
)


class TestFlyPigException:
    """基类异常测试"""

    def test_default_code(self) -> None:
        ex = FlyPigException()
        assert ex.code == "UNKNOWN"

    def test_default_message(self) -> None:
        ex = FlyPigException()
        assert ex.message == ""

    def test_message_sets_correctly(self) -> None:
        ex = FlyPigException("出错了")
        assert ex.message == "出错了"
        assert str(ex) == "出错了"

    def test_details_default_empty_dict(self) -> None:
        ex = FlyPigException("msg")
        assert ex.details == {}

    def test_details_merges_correctly(self) -> None:
        ex = FlyPigException("msg", {"key": "val"})
        assert ex.details == {"key": "val"}

    def test_to_dict_structure(self) -> None:
        ex = FlyPigException("test", {"k": "v"})
        d = ex.to_dict()
        assert d == {"code": "UNKNOWN", "message": "test", "details": {"k": "v"}}

    def test_is_exception_subclass(self) -> None:
        assert issubclass(FlyPigException, Exception)


class TestDomainErrors:
    """领域层异常测试"""

    def test_domain_error_code(self) -> None:
        assert DomainError.code == "DOMAIN_ERR"

    def test_session_closed_code(self) -> None:
        assert SessionClosedError.code == "SESSION_CLOSED"
        assert issubclass(SessionClosedError, DomainError)

    def test_invalid_turn_code(self) -> None:
        assert InvalidTurnError.code == "INVALID_TURN"
        assert issubclass(InvalidTurnError, DomainError)

    def test_message_validation_code(self) -> None:
        assert MessageValidationError.code == "MSG_INVALID"
        assert issubclass(MessageValidationError, DomainError)


class TestConfigErrors:
    """配置层异常测试"""

    def test_config_error_code(self) -> None:
        assert ConfigurationError.code == "CONFIG_ERROR"
        assert issubclass(ConfigurationError, FlyPigException)


class TestModelAPIErrors:
    """模型 API 异常测试"""

    def test_model_api_error_code(self) -> None:
        assert ModelAPIError.code == "MODEL_API_ERR"

    def test_circuit_breaker_code(self) -> None:
        assert CircuitBreakerError.code == "CIRCUIT_OPEN"


class TestToolErrors:
    """工具执行异常测试"""

    def test_tool_execution_code(self) -> None:
        assert ToolExecutionError.code == "TOOL_EXEC_ERR"


class TestSandboxErrors:
    """沙箱异常测试"""

    def test_sandbox_error_code(self) -> None:
        assert SandboxError.code == "SANDBOX_ERR"
