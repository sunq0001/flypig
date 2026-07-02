<!--
MainLayout：三栏布局 — TDesign Layout 组件

三栏：左(SideBar) + 中(Viewer + Resource) + 右(Chat/Term)
内层 panels 支持拖拽调宽（ResizeHandleLR）和拖拽排序（SortableJS）。
-->
<template>
  <t-layout style="height:100vh">
    <!-- 主行：SideBar + panels + 底栏 -->
    <t-layout style="flex:1;min-height:0;overflow:hidden">
      <t-aside width="48px" style="display:flex;flex-direction:column;background:#2c2c2c;overflow:hidden">
        <SideBar :activeView="activeView" @switch="onSwitch" />
      </t-aside>
      <div ref="bodyRef" class="layout-body">
        <template v-for="(p, i) in panels" :key="p.id">
          <div class="panel" :style="panelStyle(p)" :data-panel-id="p.id">
            <div class="pcontent">
              <ResourceBar v-if="p.id === 'resource'" :activeView="activeView"
                @switch-workspace="onSwitchWorkspace" @open-file="onOpenFile" />
              <ViewerBar v-else-if="p.id === 'viewer'" :ref="el => viewerInstance = el" />
              <InteractBar v-else-if="p.id === 'interact'" :model="defaultModel" />
            </div>
          </div>
          <ResizeHandleLR v-if="i < panels.length - 1" :panels="panels" :idx="i" />
        </template>
      </div>
    </t-layout>

    <t-footer height="24px" style="padding:0!important;background:#007acc">
      <StatusBar :workspace="workspace" />
    </t-footer>
  </t-layout>

  <!-- 切换工作区弹窗（div 弹窗，修复 TDesign Dialog Teleport bug） -->
  <div v-if="showWorkspacePicker" class="dlg-overlay" @click.self="showWorkspacePicker = false">
    <div class="dlg-box">
      <div class="dlg-header">
        <span>切换工作区</span>
        <button class="dlg-close" @click="showWorkspacePicker = false">✕</button>
      </div>
      <div class="dlg-body">
        <WorkspaceStep @selected="onWorkspaceChanged" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import Sortable from 'sortablejs'
import SideBar from './SideBar.vue'
import ResourceBar from './ResourceBar.vue'
import ViewerBar from './ViewerBar.vue'
import InteractBar from './InteractBar.vue'
import StatusBar from './StatusBar.vue'
import ResizeHandleLR from './ResizeHandleLR.vue'
import WorkspaceStep from '../init/WorkspaceStep.vue'

defineProps({ workspace: String, defaultModel: String })
const emit = defineEmits(['workspaceChanged'])
const activeView = ref('file')
const showWorkspacePicker = ref(false)

function onSwitch(v) { activeView.value = v }
function onSwitchWorkspace() {
  showWorkspacePicker.value = true
}

let viewerInstance = null
function onOpenFile(path) { viewerInstance?.openFile(path) }

function onWorkspaceChanged() {
  showWorkspacePicker.value = false
  emit('workspaceChanged')
}

const bodyRef = ref(null)
const panels = reactive([
  { id: 'resource', w: 260 },
  { id: 'viewer', w: 0 },
  { id: 'interact', w: 360 },
])

function panelStyle(p) {
  if (p.id === 'viewer' && p.w <= 0) return { flex: '1', minWidth: 80 }
  return { width: Math.max(80, p.w) + 'px', flexShrink: 0 }
}

onMounted(() => {
  const el = bodyRef.value
  if (!el) return
  nextTick(() => {
    Sortable.create(el, {
      animation: 200, filter: '.resize-lr', preventOnFilter: false,
      direction: 'horizontal',
      onEnd: () => {
        const order = [...el.querySelectorAll('.panel')].map(d => d.dataset.panelId)
        const sorted = order.map(id => panels.find(p => p.id === id)).filter(Boolean)
        panels.splice(0, panels.length, ...sorted)
      },
    })
  })
})
</script>

<style scoped>
.t-layout { background: #1e1e1e; }
.layout-body { flex: 1; min-height: 0; min-width: 0; display: flex; overflow: hidden; align-items: stretch; }
.panel { display: flex; min-width: 0; }
.panel.sortable-ghost { opacity: 0.3; }
.panel.sortable-chosen { box-shadow: 0 0 0 2px #409eff inset; }
.pcontent { flex: 1; min-width: 0; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
</style>

<style>
/* TDesign t-layout__content 必须溢出隐藏，否则内部 .layout-body 撑破容器 */
.t-layout__content {
  min-height: 0 !important;
  overflow: hidden !important;
}

/* 自定义弹窗样式 */
.dlg-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
}
.dlg-box {
  background: #252526;
  border: 1px solid #333;
  border-radius: 8px;
  width: 500px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.dlg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #333;
  color: #ccc;
  font-size: 14px;
  font-weight: 500;
}
.dlg-close {
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 16px;
  padding: 2px 6px;
  border-radius: 3px;
}
.dlg-close:hover {
  color: #ccc;
  background: #333;
}
.dlg-body {
  padding: 20px;
}


</style>
