"""会话数据类

为什么做：用户与 AI 的对话以"会话"为单位组织，需要记录会话元数据（ID/时间/标题/状态）。
实现方法：@dataclass 定义 Session (session_id/created_at/title/status)，支持 restore() 方法。
实现效果：会话管理有统一的数据结构，历史会话列表和断点恢复使用同一模型。
技术栈：@dataclass, Session, restore

层&依赖：domain.models 层，零依赖
细节见文档：docs/docs_refactor/backend-modules.md → §SessionService
"""