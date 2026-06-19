<!--
McpConfig：MCP 能力配置面板

为什么做：不同 MCP Server 有不同的配置参数（如数据库路径、API Key、URL），需要统一的可视化配置界面。
实现方法：根据 MCP Server 的 config schema 动态渲染配置表单，保存时调用 PUT /api/mcp/<name>/config。
实现效果：用户不用手改 JSON，在 UI 上即可完成所有配置。

技术栈：Vue 3 SFC, Element Plus form
层&依赖：frontend.presentation → mcp 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §能力管理面板
-->
