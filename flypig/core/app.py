"""Quart App 工厂

为什么做：后端的 Web 入口需要统一创建 app 实例、注册蓝图、配置中间件，不能在 __main__.py 里内联写死。
实现方法：create_app() 工厂函数，注册所有后端路由蓝图 + 初始化 SSE 队列 + CORS + 日志中间件。
实现效果：启动方式切换（dev/prod）不影响路由代码，新增蓝图只需在工厂里加一行。
技术栈：Quart, CORS, SSE, Hypercorn

层&依赖：core 层，依赖 backend/routes 蓝图 + infrastructure 中间件
细节见文档：docs/docs_refactor/backend-modules.md → §Backend Layer、data-flow.md → §后端数据流、tech-stack.md → §Web 框架
"""