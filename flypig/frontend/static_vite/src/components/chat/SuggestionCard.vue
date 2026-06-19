<!--
SuggestionCard：对抗建议卡片

为什么做：AI 改完代码后需要展示"第二意见"建议（哪些改得好/有隐患），帮助用户判断是否采纳。
实现方法：Element Plus card 渲染评分/建议列表/采纳/拒绝按钮，用户反馈写入数据库。
实现效果：用户看到 AI 修改后的专业评估，不是盲信 AI 的输出。

技术栈：Vue 3 SFC, Element Plus card
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/adversarial-system.md → §对抗建议
-->
