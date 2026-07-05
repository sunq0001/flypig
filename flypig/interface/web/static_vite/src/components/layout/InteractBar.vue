<!--
InteractBar：右侧交互栏容器（对话/终端标签切换）

使用 TDesign <t-tabs> 替代手写标签栏，减少 2 层 div 嵌套。
-->
<template>
  <div class="interact-bar">
    <t-tabs
      v-model="activeTab"
      theme="card"
    >
      <template #action>
        <span class="model-name">{{ model }}</span>
      </template>
      <t-tab-panel
        value="chat"
        label="💬 对话"
        :destroy-on-hide="false"
      >
        <ChatPanel :model="model" />
      </t-tab-panel>
      <t-tab-panel
        value="term"
        label="🖥 终端"
        :destroy-on-hide="false"
      >
        <TermBar />
      </t-tab-panel>
    </t-tabs>
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
.interact-bar{flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden;background:#1e1e1e}
.model-name{margin-left:auto;padding-right:12px;font-size:11px;color:#555}
</style>

<style>
/* TDesign tabs 暗色主题覆盖 — 提高特异性覆盖 TDesign 内部样式 */
.interact-bar .t-tabs { background: #1e1e1e; display: flex; flex-direction: column; flex: 1; min-height: 0; }
.interact-bar .t-tabs__header { background: #252526; }
.interact-bar .t-tabs__nav { background: #252526; }
.interact-bar .t-tabs__nav-scroll { background: #252526; }
.interact-bar .t-tabs__nav-wrap { background: #252526; }
.interact-bar .t-tabs__operations { background: #252526; }
.interact-bar .t-tabs__action { background: #252526; }
.interact-bar .t-tabs__nav-item { background: #252526 !important; color: #888 !important; border-color: transparent; }
.interact-bar .t-tabs__nav-item:hover { background: #333 !important; color: #aaa !important; }
.interact-bar .t-tabs__nav-item.t-is-active { background: #1e1e1e !important; color: #ccc !important; }
.interact-bar .t-tabs__content { background: #1e1e1e; flex: 1; min-height: 0; display: flex; flex-direction: column; }
.interact-bar .t-tab-panel { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.interact-bar .t-tab-panel.t-is-hidden { display: none; flex: none; }
</style>
