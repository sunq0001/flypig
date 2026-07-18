<!--
ToolEvents：工具调用过程可视化（tool-call / tool-result）

为什么做：后端把工具调用过程推到独立的 /api/chat/tool-events SSE 通道，
        与 ai-sdk 的文本打字机流物理隔离。本组件只负责把这批事件渲染成卡片，
        完全不碰 @ai-sdk/vue 的 useChat 文本渲染（打字机效果不受影响）。

设计：events 是按到达顺序的扁平列表（call 后跟 result），逐条渲染。
-->
<template>
  <div v-if="events.length" class="tool-events">
    <div class="te-header">🛠 工具调用 ({{ count }})</div>
    <div
      v-for="(ev, i) in events"
      :key="i"
      class="te-item"
      :class="ev.type"
    >
      <template v-if="ev.type === 'tool-call'">
        <div class="te-call">
          <span class="te-icon">▶</span>
          <span class="te-name">{{ ev.name }}</span>
          <span class="te-args">{{ formatArgs(ev.args) }}</span>
        </div>
      </template>
      <template v-else-if="ev.type === 'tool-result'">
        <details class="te-result">
          <summary>↩ 返回结果</summary>
          <pre>{{ truncate(ev.result, 2000) }}</pre>
        </details>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  events: { type: Array, default: () => [] },
})

const count = computed(() => props.events.filter(e => e.type === 'tool-call').length)

function formatArgs(args) {
  if (!args || !Object.keys(args).length) return ''
  try {
    const s = JSON.stringify(args)
    return s.length > 120 ? s.slice(0, 120) + '…' : s
  } catch {
    return String(args)
  }
}

function truncate(s, n) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + `\n…(已截断 ${s.length - n} 字)` : s
}
</script>

<style scoped>
.tool-events {
  margin: 4px 12px 0;
  border: 1px solid #333;
  border-radius: 6px;
  background: #181818;
  font-size: 12px;
}
.te-header {
  padding: 4px 10px;
  color: #888;
  border-bottom: 1px solid #2a2a2a;
  font-size: 11px;
}
.te-item { padding: 3px 10px; }
.te-item.tool-call { color: #cdd6e0; }
.te-icon { color: #409eff; margin-right: 4px; }
.te-name { color: #e6c07a; font-weight: 600; }
.te-args { color: #888; margin-left: 6px; word-break: break-all; }
.te-result { color: #9ece8b; }
.te-result summary { cursor: pointer; color: #888; padding: 2px 0; }
.te-result pre {
  margin: 4px 0 0;
  padding: 6px 8px;
  background: #0f0f0f;
  border-radius: 4px;
  color: #b5b5b5;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 11px;
}
</style>
