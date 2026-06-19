"""事件订阅单元测试

为什么做：事件订阅的注册和分发逻辑需要测试，确保事件正确路由到订阅者。
实现方法：mock hook，测试 register/emit 链。
实现效果：加新订阅时测试可验证路由正确。
技术栈：pytest, mock hook

层&依赖：tests.unit 层，依赖 orchestration/event_subscriptions.py
细节见文档：docs/docs_refactor/backend-modules.md → §EventSubscriptions
"""