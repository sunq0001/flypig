"""网页抓取工具

为什么做：AI 需要读取网页内容（文档/教程/API 参考），不能靠 MCP fetch 场景覆盖。
实现方法：httpx 发请求，trafilatura HTML→纯文本去噪（比 BeautifulSoup 效果好）。不依赖 MCP fetch。
实现效果：AI 获取网页内容时自动去除导航/广告等噪音，只保留正文。
技术栈：httpx + trafilatura, HTML→纯文本去噪

层&依赖：infrastructure.tools.system 层，依赖 httpx, trafilatura
细节见文档：docs/docs_refactor/tech-stack.md → §网页抓取
"""
