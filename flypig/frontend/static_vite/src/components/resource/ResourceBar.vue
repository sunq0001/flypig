<!--
ResourceBar：左侧资源栏容器

为什么做：用户需要在文件树、能力管理、统计等资源面板间切换，由 ActivityBar 控制。
实现方法：接收 activeView prop，根据值渲染 FileTreeBar / McpBar / StatsBar。
实现效果：ActivityBar 点击即切换资源栏内容，各面板独立开发。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → resource 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §全局布局
-->
<template>
  <div class="resource-bar">
    <div class="bar-header">{{ activeLabel }}</div>
    <div class="bar-body">
      <FileTreeBar v-if="activeView === 'file'" />
      <McpBar v-if="activeView === 'mcp'" />
      <StatsBar v-if="activeView === 'stats'" />
    </div>
  </div>
</template>
<script setup>
/**
 * @module ResourceBar：左侧资源栏容器
 * @description 用户需要在文件树、能力管理、统计等资源面板间切换，由 ActivityBar 控制。 接收 activeView prop，根据值渲染 FileTreeBar / McpBar / StatsBar。 ActivityBar 点击即切换资源栏内容，各面板独立开发。
 */
import { computed } from 'vue'
import FileTreeBar from './FileTreeBar.vue'
import McpBar from './McpBar.vue'
import StatsBar from './StatsBar.vue'
const props = defineProps({ activeView: { type: String, default: 'file' } })
const activeLabel = computed(() => ({ file:'文件', mcp:'能力', stats:'统计' }[props.activeView] || '文件'))
</script>
<style scoped>
.resource-bar{width:100%;height:100%;background:#252526;color:#ccc;display:flex;flex-direction:column;border-right:1px solid #1e1e1e}
.bar-header{height:36px;display:flex;align-items:center;padding:0 16px;font-size:12px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #1e1e1e;flex-shrink:0}
.bar-body{flex:1;overflow-y:auto}
</style>
