---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  name: "FlyPig Agent"
  text: "终端+聊天 AI 助手"
  tagline: 架构设计文档 — 面向非程序员的 AI Agent
  actions:
    - theme: brand
      text: 架构指南
      link: /docs_refactor/architecture-guide
    - theme: alt
      text: 前端架构
      link: /docs_refactor/frontend-arch

features:
  - title: 🧩 MCP 能力系统
    details: Model Context Protocol 作为能力扩展，前端显示为"能力"
  - title: 🏗️ 分层架构
    details: Presentation / Orchestration / Domain / Infrastructure 四层
  - title: 🤖 LangGraph 状态机
    details: chat → ask_choice → execute → lint → review → suggest 节点
  - title: 🛡️ 对抗体系
    details: ChangeReview + Linter + ChangeScore + SuggestionCard 四层防御
---
