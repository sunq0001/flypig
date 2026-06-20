<!--
MainLayout：三栏布局
panels 数组驱动，SortableJS 重排后 handle 自动适配。
-->
<template>
  <div class="main-layout">
    <div class="layout-row">
      <SideBar :activeView="activeView" @switch="onSwitch" />
      <div ref="bodyRef" class="layout-body">
        <template v-for="(p, i) in panels" :key="p.id">
          <div class="panel" :style="panelStyle(p)" :data-panel-id="p.id">
            <div class="pcontent">
              <ResourceBar v-if="p.id === 'resource'" :activeView="activeView" />
              <ViewerBar v-else-if="p.id === 'viewer'" />
              <InteractBar v-else-if="p.id === 'interact'" :model="defaultModel" />
            </div>
          </div>
          <ResizeHandleLR v-if="i < panels.length - 1" @resize="d => onResize(i, d)" />
        </template>
      </div>
    </div>
    <StatusBar :workspace="workspace" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import Sortable from 'sortablejs'
import SideBar from './SideBar.vue'
import ResourceBar from './ResourceBar.vue'
import ViewerBar from './ViewerBar.vue'
import InteractBar from './InteractBar.vue'
import StatusBar from './StatusBar.vue'
import ResizeHandleLR from './ResizeHandleLR.vue'

defineProps({ workspace: String, defaultModel: String })
const activeView = ref('file')
function onSwitch(v) { activeView.value = v }

const bodyRef = ref(null)
const panels = reactive([
  { id: 'resource', w: 260 },
  { id: 'viewer', w: 0 },     // 0 = auto
  { id: 'interact', w: 360 },
])

function panelStyle(p) {
  if (p.id === 'viewer' && p.w <= 0) return { flex: '1', minWidth: 80 }
  return { width: Math.max(80, p.w) + 'px', flexShrink: 0 }
}

// 记录拖拽起始宽度
let dragStarts = []

function onResize(idx, delta) {
  if (delta === 0) { dragStarts = []; return }
  if (dragStarts.length === 0) {
    // 获取所有面板当前真实宽度
    const el = bodyRef.value
    const divs = el?.querySelectorAll('.panel') || []
    dragStarts = panels.map((p, i) => {
      if (p.w > 0) return p.w
      const w = divs[i]?.getBoundingClientRect().width || 200
      return Math.round(w)
    })
  }
  const left = panels[idx]
  const right = panels[idx + 1]
  if (!left || !right) return
  left.w = Math.max(80, dragStarts[idx] + delta)
  right.w = Math.max(80, dragStarts[idx + 1] - delta)
  // viewer auto 变固定
  if (left.w > 0 && left.w <= 80) left.w = 80
  if (right.w > 0 && right.w <= 80) right.w = 80
}

onMounted(() => {
  const el = bodyRef.value
  if (!el) return
  nextTick(() => {
    Sortable.create(el, {
      animation: 200,
      filter: '.resize-lr',
      preventOnFilter: false,
      direction: 'horizontal',
      onEnd: () => {
        // 从 DOM 读取排序后的 panel-id 顺序
        const order = [...el.querySelectorAll('.panel')].map(d => d.dataset.panelId)
        const sorted = order.map(id => panels.find(p => p.id === id)).filter(Boolean)
        panels.splice(0, panels.length, ...sorted)
      },
    })
  })
})
</script>

<style scoped>
.main-layout { height: 100vh; display: flex; flex-direction: column; background: #1e1e1e; overflow: hidden; }
.layout-row { flex: 1; display: flex; overflow: hidden; }
.layout-body { flex: 1; display: flex; overflow: hidden; min-width: 0; align-items: stretch; }
.panel { display: flex; }
.panel.sortable-ghost { opacity: 0.3; }
.panel.sortable-chosen { box-shadow: 0 0 0 2px #409eff inset; }
.pcontent { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
</style>
