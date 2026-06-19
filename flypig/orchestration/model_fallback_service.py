"""多模型 Fallback 服务 (P1 预留)

为什么做：AI 调用的模型不可用（API 超时/限频/下线）时需要自动切换到备用模型，保证服务不中断。
实现方法：ModelFallbackService 封装模型切换逻辑，P0 仅记录 fallback 事件，P1 实现自动切换。
实现效果：P0 不改变现有行为，P1 启用后模型故障自动切换用户无感。
技术栈：P0 仅记录错误

层&依赖：orchestration 层，依赖 domain/config（模型注册表）
细节见文档：—
"""