"""FlyPig 抽象接口包

为什么做：领域层通过抽象接口定义行为契约，基础设施层实现具体逻辑，解耦模块间依赖。
实现方法：ABC 抽象基类 + @abstractmethod，每个接口单一职责（模型适配/工具执行/对话存储/搜索/权限等）。
实现效果：替换实现不需要改业务代码（如 SQLite → PostgreSQL 只需换 conversation_store 的实现）。
技术栈：ABC, @abstractmethod

层&依赖：domain.interfaces 层，零依赖（纯 ABC 定义）
细节见文档：docs/docs_refactor/architecture-guide.md → §接口隔离
"""