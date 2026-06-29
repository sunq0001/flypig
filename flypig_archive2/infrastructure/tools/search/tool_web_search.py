"""网络搜索工具 (P1)

为什么做：AI 需要搜索互联网获取最新的 API 文档/技术方案/依赖版本等信息。
实现方法：duckduckgo-search 库零配置搜索，返回标题+摘要+链接。P1 默认不启用。
实现效果：AI 可以在对话中搜索互联网，不要求用户提供 API Key。
技术栈：duckduckgo-search, httpx

层&依赖：infrastructure.tools.search 层，依赖 httpx
细节见文档：docs/docs_refactor/tech-stack.md → §内置搜索
"""
