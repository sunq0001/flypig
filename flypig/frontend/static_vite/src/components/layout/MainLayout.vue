<!--
MainLayout：三栏主布局容器

为什么做：用户需要 VS Code 风格的可拖拽三栏布局（Sidebar + 中间查看器 + 对话面板）。
实现方法：ActivityBar + ResourceBar + ViewBar + InteractBar + StatusBar，支持鼠标拖拽调整栏宽。
实现效果：左右栏可拖拽调整宽度，ActivityBar 切换侧边栏内容。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §全局布局
-->
<template>
  <div class="main-layout">
    <div class="layout-row">
      <ActivityBar :activeView="activeView" @switch="onSwitch" />

      <div class="layout-body">
        <div class="bar-wrapper" :style="{ width: sidebarWidth + 'px' }">
          <ResourceBar :activeView="activeView" />
        </div>
        <div class="resize-handle" @mousedown.prevent="startResize('sidebar', $event)"></div>

        <div class="bar-wrapper view-wrapper">
          <ViewBar />
        </div>

        <div class="resize-handle" @mousedown.prevent="startResize('chat', $event)"></div>

        <div class="bar-wrapper" :style="{ width: chatWidth + 'px' }">
          <InteractBar :model="defaultModel" />
        </div>
      </div>
    </div>
    <StatusBar :workspace="workspace" />
  </div>
</template>

<script setup>
/**
 * @module MainLayout：三栏主布局容器
 * @description 用户需要 VS Code 风格的可拖拽三栏布局（Sidebar + 中间查看器 + 对话面板）。 ActivityBar + ResourceBar + ViewBar + InteractBar + StatusBar，支持鼠标拖拽调整栏宽。 左右栏可拖拽调整宽度，ActivityBar 切换侧边栏内容。
 */
import { ref } from 'vue'
import ActivityBar from './ActivityBar.vue'
import ResourceBar from '../resource/ResourceBar.vue'
import ViewBar from '../viewer/ViewBar.vue'
import InteractBar from './InteractBar.vue'
import StatusBar from './StatusBar.vue'

defineProps({
  workspace: { type: String, default: '' },
  defaultModel: { type: String, default: '' },
})

const activeView = ref('file')
const sidebarWidth = ref(260)
const chatWidth = ref(360)

function onSwitch(view) { activeView.value = view }

let _target = null, _startX = 0, _startSize = 0
function startResize(target, e) {
  _target = target; _startX = e.clientX
  _startSize = target === 'sidebar' ? sidebarWidth.value : chatWidth.value
  document.body.style.cursor = 'col-resize'; document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}
function onMove(e) {
  if (!_target) return; const delta = e.clientX - _startX
  if (_target === 'sidebar') sidebarWidth.value = Math.max(180, Math.min(500, _startSize + delta))
  else chatWidth.value = Math.max(280, Math.min(600, _startSize - delta))
}
function onUp() {
  _target = null; document.body.style.cursor = ''; document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onMove)
  document.removeEventListener('mouseup', onUp)
}
</script>

<style scoped>
.main-layout{height:100vh;display:flex;flex-direction:column;background:#1e1e1e;overflow:hidden}
.layout-row{flex:1;display:flex;overflow:hidden}
.layout-body{flex:1;display:flex;overflow:hidden;min-width:0}
.bar-wrapper{flex-shrink:0;overflow:hidden}
.view-wrapper{flex:1;min-width:0}
.resize-handle{flex-shrink:0;width:4px;cursor:col-resize;transition:background .1s;position:relative;z-index:10}
.resize-handle::after{content:'';position:absolute;top:0;bottom:0;left:-4px;right:-4px}
.resize-handle:hover{background:#409eff}
</style>
