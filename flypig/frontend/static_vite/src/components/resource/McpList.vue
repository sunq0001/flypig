<!--
McpList：MCP 能力列表（搜索 + 分类 tab + 列表）

为什么做：用户需要搜索和浏览已安装/商店中的能力，按状态筛选。
实现方法：顶部搜索框 + 分类 tab（已安装/商店）+ 可滚动列表，每项显示状态标识。
实现效果：用户快速找到所需能力，一目了然每个能力的启停状态。

技术栈：Vue 3 SFC, Element Plus input/tab
层&依赖：frontend.presentation → mcp 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §能力管理面板
-->
