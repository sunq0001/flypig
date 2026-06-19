<!--
McpItem：MCP 能力列表单项

为什么做：列表中每条能力需要展示名称、状态、调用次数等关键信息。
实现方法：显示能力图标+名称+版本+状态标识（启用/禁用/内置），点击选中后在右侧展示详情。
实现效果：列表项信息清晰，用户快速识别能力状态。

技术栈：Vue 3 SFC, Element Plus 组件
层&依赖：frontend.presentation → mcp 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §能力管理面板
-->
