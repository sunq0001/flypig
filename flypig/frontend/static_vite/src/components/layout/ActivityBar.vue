<!--
ActivityBar：左侧活动栏图标列

为什么做：用户需要在文件浏览、能力管理、统计等视图间快速切换。
实现方法：纵向图标列，点击图标 emit switch 事件，父组件切换 resourceBar 内容。
实现效果：类似 VS Code 的活动栏，点击即可切换侧边栏显示内容。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §全局布局
-->
<template>
  <div class="activity-bar">
    <div v-for="item in items" :key="item.id"
      class="activity-item" :class="{ active: item.id === activeView }"
      :title="item.label" @click="$emit('switch', item.id)">
      {{ item.icon }}
    </div>
    <div class="activity-spacer"></div>
    <div class="activity-item" :class="{ active: activeView === 'settings' }"
      title="设置" @click="$emit('switch', 'settings')">⚙</div>
  </div>
</template>
<script setup>
/**
 * @module ActivityBar：左侧活动栏图标列
 * @description 用户需要在文件浏览、能力管理、统计等视图间快速切换。 纵向图标列，点击图标 emit switch 事件，父组件切换 resourceBar 内容。 类似 VS Code 的活动栏，点击即可切换侧边栏显示内容。
 */
defineProps({ activeView: { type: String, default: 'file' } })
defineEmits(['switch'])
const items = [
  { id: 'file',  label: '文件', icon: '📁' },
  { id: 'mcp',   label: '能力', icon: '🧩' },
  { id: 'stats', label: '统计', icon: '📊' },
]
</script>
<style scoped>
.activity-bar{width:48px;height:100%;background:#2c2c2c;display:flex;flex-direction:column;align-items:center;padding:8px 0;gap:4px;border-right:1px solid #1e1e1e;flex-shrink:0}
.activity-item{width:40px;height:40px;display:flex;align-items:center;justify-content:center;border-radius:6px;cursor:pointer;color:#888;font-size:18px;transition:all .15s}
.activity-item:hover{background:#3c3c3c;color:#ccc}
.activity-item.active{color:#fff;background:#3c3c3c;border-left:2px solid #409eff;border-radius:0 6px 6px 0;margin-left:-1px}
.activity-spacer{flex:1}
</style>
