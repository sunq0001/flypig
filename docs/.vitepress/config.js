import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'FlyPig Agent',
  description: '终端+聊天 AI 助手 — 架构文档',
  base: '/',
  lang: 'zh-CN',
  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '架构', link: '/docs_refactor/architecture-guide' },
    ],
    sidebar: {
      '/docs_refactor/': [
        {
          text: '总览',
          items: [
            { text: '架构指南', link: '/docs_refactor/architecture-guide' },
            { text: '架构图', link: '/docs_refactor/architecture-diagram' },
            { text: '文件夹树', link: '/docs_refactor/folder-tree' },
          ],
        },
        {
          text: '设计文档',
          items: [
            { text: '前端架构', link: '/docs_refactor/frontend-arch' },
            { text: '后端模块', link: '/docs_refactor/backend-modules' },
            { text: 'LangGraph 图', link: '/docs_refactor/langgraph-graph' },
            { text: '权限矩阵', link: '/docs_refactor/mode-matrix' },
            { text: '对抗体系', link: '/docs_refactor/adversarial-system' },
            { text: '数据流', link: '/docs_refactor/data-flow' },
            { text: '子进程', link: '/docs_refactor/subprocess' },
            { text: 'MCP 能力', link: '/docs_refactor/mcp' },
            { text: '记忆与存储', link: '/docs_refactor/mem_convStore' },
            { text: '短期记忆', link: '/docs_refactor/short-term-memory' },
            { text: '扩展点', link: '/docs_refactor/extensions' },
            { text: '技术栈', link: '/docs_refactor/tech-stack' },
          ],
        },
        {
          text: 'API',
          items: [
            { text: 'API 参考', link: '/docs_refactor/api-reference' },
          ],
        },
        {
          text: '演进',
          items: [
            { text: '迁移路线图', link: '/docs_refactor/migration-roadmap' },
          ],
        },
      ],
    },
    search: { provider: 'local' },
    socialLinks: [
      { icon: 'github', link: 'https://github.com' },
    ],
  },
})
