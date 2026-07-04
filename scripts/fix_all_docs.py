"""全量修复所有 docstring 违规 — 按文件类型添加缺少的为什么做/实现方法/层&依赖"""
import ast
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "flypig"

# ── 内置修复模板 ──
# key = 相对路径, value = (为什么做, 实现方法)
# 如果留空则表示追加"层&依赖"即可

FIXES: dict[str, tuple[str, str, str]] = {}

# === __init__.py ===
FIXES["acl/__init__.py"] = (
    "防腐层（ACL）隔离外部系统格式对领域层的污染，将所有外部格式翻译为领域对象",
    "纯函数转换，输入外部 JSON → 输出领域 ValueObject。每个外部系统一个文件",
    "acl 层",
)
FIXES["application/__init__.py"] = (
    "应用层负责编排领域逻辑，不包含业务规则",
    "ApplicationService 基类 + 具体编排服务。调用 DomainService 和 Repository",
    "application 层",
)
FIXES["application/dto/__init__.py"] = (
    "DTO 是应用服务与接口层之间的数据契约，隔离 API 格式与领域模型",
    "@dataclass 定义纯数据结构，不含业务逻辑。接口层负责序列化",
    "application.dto 层",
)
FIXES["bootstrap/__init__.py"] = (
    "引导层负责应用启动时装配所有依赖和服务",
    "Settings → Container → Logging → Lifecycle → App 的工厂链路",
    "bootstrap 层",
)
FIXES["bootstrap/lifecycle.py"] = (
    "管理应用生命周期事件（启动/关闭），确保资源正确初始化和释放",
    "LifecycleEvents 类注册 startup/shutdown 回调，按注册顺序依次触发",
    "bootstrap 层",
)
FIXES["domain/__init__.py"] = (
    "统一导出所有领域模型、值对象、实体、聚合根、异常、域服务",
    "集中 import + __all__，外部只需 from flypig.domain import Xxx",
    "domain 层",
)
FIXES["domain/event/__init__.py"] = (
    "统一导出所有 DomainEvent 和 EventHandler",
    "集中 import + __all__，按事件类型组织文件",
    "domain.event 层",
)
FIXES["domain/interfaces/__init__.py"] = (
    "统一导出所有领域抽象接口（ABC）",
    "集中 import + __all__，基础设施层实现这些接口",
    "domain.interfaces 层",
)
FIXES["domain/specification/__init__.py"] = (
    "统一导出所有规格模式实现",
    "集中 import + __all__，每个规格一个文件",
    "domain.specification 层",
)
FIXES["infrastructure/event/__init__.py"] = (
    "统一导出事件总线实现",
    "集中 import + __all__",
    "infrastructure.event 层",
)
FIXES["infrastructure/usage/__init__.py"] = (
    "统一导出用量与定价服务",
    "集中 import + __all__",
    "infrastructure.usage 层",
)
FIXES["interface/rest/routes/__init__.py"] = (
    "统一导出所有 API 路由蓝图",
    "集中 import + __all__，注册到 Quart app",
    "interface.rest.routes 层",
)
FIXES["interface/sse/__init__.py"] = (
    "统一导出 SSE 事件流接口实现",
    "集中 import + __all__",
    "interface.sse 层",
)
FIXES["orchestration/__init__.py"] = (
    "统一导出编排层核心服务",
    "集中 import + __all__",
    "orchestration 层",
)
FIXES["shared/kernel/__init__.py"] = (
    "DDD 核心层 — Shared Kernel，所有业务模块依赖的纯领域接口",
    "import + re-export DDD 基类，由 shared.base 统一对外导出",
    "shared.kernel 层",
)

# === 实代码文件 ===
FIXES["acl/pricing.py"] = (
    "Portkey 定价 API 返回的 JSON 格式（cents/token）与领域模型 PricingEntry（USD/1M tokens）不同，ACL 负责翻译，不让外部格式污染 domain",
    "portkey_to_pricing_entry 函数读取 Portkey JSON 的 pricing_config.pay_as_you_go，将 cents/token 转为 USD/1M tokens，返回 PricingEntry(ValueObject)",
    "acl 层，依赖 domain.pricing_entry",
)
FIXES["application/chat_service.py"] = (
    "封装 SSE 流式对话的编排逻辑：接收用户消息 → 创建模型适配器 → 逐 token 流式返回",
    "ChatApplicationService 通过 IModelFactory 创建适配器，调 adapter.stream() 得到 token 流，格式化为 SSE 事件字符串返回",
    "application 层，依赖 domain.interfaces",
)
FIXES["application/dto/chat_response.py"] = (
    "应用服务不应直接拼 SSE 格式字符串，应返回结构化 DTO，由接口层负责序列化",
    "@dataclass 定义 ChatResponse，type/content/metadata 三个字段，to_sse() 方法序列化为 SSE 格式",
    "application.dto 层",
)
FIXES["bootstrap/app_factory.py"] = (
    "后端的 Web 入口需要统一创建 app 实例、注册蓝图、配置中间件",
    "create_app() 工厂函数，先通过 load_config + AppContainer 初始化配置和 DI 容器，再注册所有路由蓝图 + CORS + 日志 + 生命周期",
    "bootstrap 层，依赖 interface/rest/routes",
)
FIXES["bootstrap/container.py"] = (
    "所有依赖（配置、模型、工具、存储、服务）需要统一注册和管理，不能手动 new 或从全局变量获取",
    "dependency-injector 声明式 DeclarativeContainer，各服务用 providers 声明作用域（Singleton/Factory），Wire 模式自动注入到模块",
    "bootstrap 层",
)
FIXES["bootstrap/settings.py"] = (
    "应用配置需要从环境变量 / YAML / JSON 三级加载，不能硬编码",
    "AppSettings(pydantic-settings) 自动从环境变量读取，PyYAML 从 config.yaml 加载，JSON 提供默认值。优先级：环境变量 > YAML > JSON",
    "bootstrap 层，依赖 shared.settings",
)
FIXES["domain/interfaces/ievent_stream.py"] = (
    "ChatService 需要向前端推送逐 token 事件（token/tool_call/error/done），但不应直接依赖 SSE 具体实现",
    "ABC 定义 push/pop/cleanup 三个方法。SSEQueue 实现基于 asyncio.Queue",
    "domain.interfaces 层",
)
FIXES["domain/interfaces/ilocal_model_service.py"] = (
    "本地模型（Ollama）的管理操作（检测运行状态、列表已安装模型、拉取模型）需要统一接口，方便测试和替换",
    "ABC 定义 check_running / list_installed_names / pull_model 三个方法。OllamaLocalModelService 实现基于 httpx",
    "domain.interfaces 层",
)
FIXES["domain/interfaces/imodel_factory.py"] = (
    "路由层不应直接 new OpenAIAdapter，应通过工厂接口创建模型适配器",
    "Factory[IModel] 泛型，create 方法接收模型名 + 配置，返回对应的 IModel 实例",
    "domain.interfaces 层，extends Factory[IModel]",
)
FIXES["domain/interfaces/imodel_policy.py"] = (
    "不同模型和场景需要不同的执行策略（重试/熔断/超时/回退），需要统一策略接口",
    "ABC 定义 execute 方法，包装模型调用，基础设施层实现具体策略",
    "domain.interfaces 层",
)
FIXES["domain/registry.py"] = (
    "模型配置（厂商/API 路径/定价/本地模型）集中在 model_registry.json 中，需要统一的读取入口",
    "从 model_registry.json 加载所有模型元数据、厂商映射、定价配置、本地配置。DomainService 封装 JSON 读取逻辑",
    "domain 层",
)
FIXES["infrastructure/llm/__init__.py"] = (
    "不同 LLM API 的适配器统一出口",
    "集中 import + __all__",
    "infrastructure.llm 层",
)
FIXES["infrastructure/llm/model_factory.py"] = (
    "根据模型名路由到对应的适配器实现",
    "ModelFactory 实现 IModelFactory 接口，按 provider 路由：Anthropic → AnthropicAdapter，其他 → OpenAIAdapter",
    "infrastructure.llm 层，实现 domain.interfaces.imodel_factory",
)
FIXES["infrastructure/llm/openai_adapter.py"] = (
    "OpenAI 兼容格式的 LLM API（DeepSeek/Qwen/GLM/豆包等）需要统一适配器",
    "封装 AsyncOpenAI SDK，stream 方法返回异步 token 生成器。配置来自 model_registry.json + AppSettings",
    "infrastructure.llm 层，实现 domain.interfaces.imodel",
)
FIXES["infrastructure/ollama/__init__.py"] = (
    "Ollama 本地模型基础设施模块",
    "检查服务运行状态、列表已安装模型、拉取模型",
    "infrastructure.ollama 层",
)
FIXES["infrastructure/ollama/service.py"] = (
    "封装 Ollama HTTP API，提供本地模型的生命周期管理",
    "OllamaLocalModelService 通过 httpx 调用 Ollama API（/api/tags、/api/pull），实现 ILocalModelService 接口",
    "infrastructure.ollama 层，实现 domain.interfaces.ilocal_model_service",
)
FIXES["infrastructure/policies/__init__.py"] = (
    "统一导出执行策略实现（重试/熔断/权限）",
    "集中 import + __all__",
    "infrastructure.policies 层",
)
FIXES["infrastructure/usage/pricing.py"] = (
    "前端需要显示各模型实时价格，需要从 Portkey API 抓取 + 本地缓存 + 每日自动刷新",
    "PricingService 封装了从 Portkey 抓取、USD→CNY 汇率转换、本地缓存（pricing_cache.json）、每日自动刷新循环",
    "infrastructure.usage 层，依赖 domain.registry",
)
FIXES["interface/rest/routes/chat_routes.py"] = (
    "前端 useChat 通过 POST /api/chat 发送用户消息，后端返回 AI SDK v4 SSE 流",
    "POST 路由接收 messages + model，调 ChatApplicationService.generate_sse() 返回 text/event-stream 响应",
    "interface.rest.routes 层，通过 ChatApplicationService 依赖 application 层",
)
FIXES["interface/rest/routes/config_routes.py"] = (
    "前端需要获取/修改应用配置（工作目录、API Key、本地模型等）",
    "REST 路由组：workspace/apikey/browse/mkdir/local-models/local-models/pull",
    "interface.rest.routes 层",
)
FIXES["interface/rest/routes/files_routes.py"] = (
    "前端需要浏览文件树和读取文件内容",
    "POST /api/tree 返回目录结构，POST /api/file 读取文件内容",
    "interface.rest.routes 层",
)
FIXES["interface/rest/routes/health_routes.py"] = (
    "健康检查端点，用于监控和负载均衡",
    "GET /api/health 返回 {'status': 'ok'}",
    "interface.rest.routes 层",
)
FIXES["interface/rest/routes/pricing_routes.py"] = (
    "前端需要获取模型价格信息",
    "GET /api/pricing 返回 PricingService.fetch_pricing() 结果",
    "interface.rest.routes 层",
)
FIXES["interface/sse/sse_queue.py"] = (
    "ChatService 需要按 session 隔离推送实时事件，IEventStream 接口的 asyncio.Queue 实现",
    "SSEQueue 实现 IEventStream 接口，内部用 dict[str, asyncio.Queue] 按 session_id 隔离",
    "interface.sse 层，实现 domain.interfaces.ievent_stream",
)
FIXES["orchestration/graph_factory.py"] = (
    "LangGraph 的 StateGraph 编译需要封装，避免业务代码直接依赖 LangGraph 细节",
    "GraphFactory 组装 nodes + edges，调用 StateGraph.compile() 返回可调用的 graph",
    "orchestration 层，依赖 domain/interfaces",
)
FIXES["shared/application_service.py"] = (
    "应用服务基类，定义编排层的行为契约",
    "ABC 标记基类，约束：不含业务逻辑，只做协调和编排",
    "shared 层",
)
FIXES["shared/base.py"] = (
    "统一导出入口，所有领域层的共享基类和接口集中在此导出",
    "从 shared/kernel 和各模块 re-export，业务模块只需 from flypig.shared.base import Entity",
    "shared 层",
)
FIXES["shared/factory.py"] = (
    "工厂基类，封装复杂创建逻辑",
    "ABC + Generic[T]，定义 create 抽象方法",
    "shared 层",
)
FIXES["shared/result.py"] = (
    "Result 类型显式处理成功/失败，代替 try/except 异常传播",
    "@dataclass 泛型，ok() / err() 工厂方法，unwrap() 安全取值",
    "shared 层",
)
FIXES["shared/settings.py"] = (
    "AppSettings 被 application 层和 infrastructure 层引用，定义在 shared 层避免各层依赖 bootstrap",
    "pydantic-settings BaseSettings，环境变量自动读取。所有 LLM API Key 和基础配置在此定义",
    "shared 层，依赖 pydantic-settings",
)
FIXES["shared/specification.py"] = (
    "规格模式将业务规则封装为可组合的对象，支持 and_ / or_ / not_ 组合",
    "ABC + Generic[T]，定义 is_satisfied_by 抽象方法 + and_/or_/not_ 组合方法",
    "shared 层",
)
FIXES["shared/validation.py"] = (
    "校验工具，收集错误不抛异常，避免 try/except 散落在业务代码中",
    "ValidationResult 收集错误列表，Validator 组合多条校验规则",
    "shared 层",
)

# === 兼容导入桩文件 ===
STUB_FIXES: dict[str, str] = {
    "domain/message_id.py": "兼容导入 — MessageId 定义在 message.py 中",
    "domain/session_id.py": "兼容导入 — SessionId 定义在 session.py 中",
    "domain/session_status.py": "兼容导入 — SessionStatus 定义在 session.py 中",
    "domain/tool_def.py": "兼容导入 — ToolDef 定义在 tool_call.py 中",
    "domain/tool_result.py": "兼容导入 — ToolResult 定义在 tool_call.py 中",
}

# === 测试文件 ===
TEST_FIXES: dict[str, tuple[str, str, str]] = {
    "tests/unit/test_portkey_acl.py": (
        "测试 ACL 层的 Portkey 格式转换是否正确",
        "构造 Portkey JSON 数据，调用 portkey_to_pricing_entry，验证返回的 PricingEntry 属性值",
        "tests.unit 层，依赖 acl.pricing",
    ),
    "tests/unit/test_pricing_entry.py": (
        "测试 PricingEntry 值对象的不可变性、相等性、默认值",
        "直接构造 PricingEntry 实例，验证 __eq__、__ne__、frozen 等特性",
        "tests.unit 层，依赖 domain.pricing_entry",
    ),
}


def fix_file(rel_path: str) -> bool:
    f = BASE / rel_path
    if not f.exists():
        print(f"  NOT FOUND: {rel_path}")
        return False

    content = f.read_text(encoding="utf-8")
    tree = ast.parse(content)
    docstring = ast.get_docstring(tree)

    if rel_path in FIXES:
        why, how, layer = FIXES[rel_path]
        new_doc = f'"""{f.stem if f.suffix == ".py" else rel_path}\n\n为什么做：{why}\n\n实现方法：{how}\n\n层&依赖：{layer}\n"""'
        # 替换文件头部 docstring
        if docstring:
            # 找到 docstring 起始和结束位置
            lines = content.split("\n")
            in_doc = False
            doc_start = doc_end = -1
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('"""') and not in_doc:
                    doc_start = i
                    in_doc = True
                    if stripped.endswith('"""') and len(stripped) > 3:
                        doc_end = i
                        break
                elif in_doc:
                    if stripped.endswith('"""'):
                        doc_end = i
                        break
            if doc_end >= 0:
                # 保留 docstring 后的空行
                after_doc = doc_end + 1
                while after_doc < len(lines) and lines[after_doc].strip() == "":
                    after_doc += 1
                rest = "\n".join(lines[after_doc:])
                new_content = new_doc + "\n\n" + rest
                f.write_text(new_content, encoding="utf-8")
                print(f"  FIXED (replace): {rel_path}")
                return True
        # fallback: 文件开头插入
        new_content = new_doc + "\n\n" + content
        f.write_text(new_content, encoding="utf-8")
        print(f"  FIXED (prepend): {rel_path}")
        return True

    elif rel_path in STUB_FIXES:
        desc = STUB_FIXES[rel_path]
        # stub 文件应该是 import 兼容
        cls_name = rel_path.replace(".py", "").split("/")[-1]
        src_map = {
            "message_id": ("MessageId", "flypig.domain.message"),
            "session_id": ("SessionId", "flypig.domain.session"),
            "session_status": ("SessionStatus", "flypig.domain.session"),
            "tool_def": ("ToolDef", "flypig.domain.tool_call"),
            "tool_result": ("ToolResult", "flypig.domain.tool_call"),
        }
        key = rel_path.replace(".py", "").split("/")[-1]
        cls, src = src_map.get(key, (key, f"flypig.domain.{key}"))
        new_content = f'"""{desc}\n\n层&依赖：domain 层\n"""\nfrom {src} import {cls}  # noqa: F401\n'
        if content.strip() != new_content.strip():
            f.write_text(new_content, encoding="utf-8")
            print(f"  FIXED (stub): {rel_path}")
            return True
        print(f"  SKIP (stub ok): {rel_path}")
        return False

    elif rel_path in TEST_FIXES:
        why, how, layer = TEST_FIXES[rel_path]
        new_doc = f'"""{f.stem}\n\n为什么做：{why}\n\n实现方法：{how}\n\n层&依赖：{layer}\n"""'
        if docstring:
            lines = content.split("\n")
            in_doc = False
            doc_start = doc_end = -1
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('"""') and not in_doc:
                    doc_start = i
                    in_doc = True
                    if stripped.endswith('"""') and len(stripped) > 3:
                        doc_end = i
                        break
                elif in_doc:
                    if stripped.endswith('"""'):
                        doc_end = i
                        break
            if doc_end >= 0:
                after_doc = doc_end + 1
                while after_doc < len(lines) and lines[after_doc].strip() == "":
                    after_doc += 1
                rest = "\n".join(lines[after_doc:])
                new_content = new_doc + "\n\n" + rest
                f.write_text(new_content, encoding="utf-8")
                print(f"  FIXED (test): {rel_path}")
                return True
        new_content = new_doc + "\n\n" + content
        f.write_text(new_content, encoding="utf-8")
        print(f"  FIXED (test): {rel_path}")
        return True

    return False


if __name__ == "__main__":
    all_keys = set(FIXES.keys()) | set(STUB_FIXES.keys()) | set(TEST_FIXES.keys())
    count = 0
    for key in sorted(all_keys):
        if fix_file(key):
            count += 1
    print(f"\nTotal fixed: {count}")
