<!--
InteractBar：右侧交互栏容器（对话/终端标签切换）

为什么做：用户需要在对话和终端之间切换查看，右侧面板空间有限需要标签页。
实现方法：顶部标签栏（💬 对话 / 🖥 终端），根据 activeTab 显示 ChatPanel 或 TermBar。
实现效果：右侧面板一个位置承载两种功能，标签切换即换内容。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §能力管理面板
-->
<template>
  <div class="interact-bar">
    <div class="tabs-bar">
      <div class="tab-list">
        <div v-for="tab in tabs" :key="tab.id" class="tab"
          :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">
          {{ tab.label }}
        </div>
      </div>
      <span class="model-name">{{ model }}</span>
    </div>
    <ChatPanel v-show="activeTab === 'chat'" :model="model" />
    <TermBar v-show="activeTab === 'term'" />
  </div>
</template>
<script setup>
/**
 * @module InteractBar：右侧交互栏容器（对话/终端标签切换）
 * @description 用户需要在对话和终端之间切换查看，右侧面板空间有限需要标签页。 顶部标签栏（💬 对话 / 🖥 终端），根据 activeTab 显示 ChatPanel 或 TermBar。 右侧面板一个位置承载两种功能，标签切换即换内容。
 */
import { ref } from 'vue'
import ChatPanel from '../interact/chat/ChatPanel.vue'
import TermBar from '../interact/terminal/TermBar.vue'
defineProps({ model: { type: String, default: '' } })
const activeTab = ref('chat')
const tabs = [
  { id: 'chat', label: '💬 对话' },
  { id: 'term', label: '🖥 终端' },
]
</script>
<style scoped>
.interact-bar{height:100%;display:flex;flex-direction:column;background:#1e1e1e;border-left:1px solid #333;overflow:hidden}
.tabs-bar{display:flex;align-items:center;height:36px;background:#252526;border-bottom:1px solid #1e1e1e;flex-shrink:0}
.tab-list{display:flex;align-items:stretch;height:100%}
.tab{display:flex;align-items:center;gap:4px;padding:0 12px;font-size:12px;color:#888;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
.tab.active{color:#ccc;border-bottom-color:#409eff}
.tab:hover{color:#aaa}
.model-name{margin-left:auto;padding-right:12px;font-size:11px;color:#555}
</style>
