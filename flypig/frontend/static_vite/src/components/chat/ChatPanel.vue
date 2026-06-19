<!--
ChatPanel：对话框面板容器

为什么做：用户在对话区域需要消息列表 + 输入框进行交互。
实现方法：MessageList（消息滚动区域）+ InputBox（文本输入框），支持流式渲染。
实现效果：对话上下滚动查看历史，底部输入框发送消息，AI 实时回复。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → chat 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §Vercel AI SDK 集成
-->
<template>
  <div class="chat-panel">
    <MessageList />
    <InputBox />
  </div>
</template>
<script setup>
/**
 * @module ChatPanel
 * @description 对话框面板容器 — 消息列表 + 输入框
 * @see frontend-arch.md → §Vercel AI SDK 集成
 */
import MessageList from './MessageList.vue'
import InputBox from './InputBox.vue'
</script>
<style scoped>
.chat-panel{width:100%;height:100%;display:flex;flex-direction:column;overflow:hidden;background:#1e1e1e}
</style>
