<!--
MainLayout：三栏布局 — TDesign Layout 组件

三栏：左(SideBar) + 中(Viewer + Resource) + 右(Chat/Term)
内层 panels 支持拖拽调宽（ResizeHandleLR）和拖拽排序（SortableJS）。
-->
<template>
  <t-layout style="height:100vh">
    <!-- 主行：SideBar + panels + 底栏 -->
    <t-layout style="flex:1;min-height:0;overflow:hidden">
      <t-aside
        width="48px"
        style="display:flex;flex-direction:column;background:#2c2c2c;overflow:hidden"
      >
        <SideBar
          :active-view="activeView"
          @switch="onSwitch"
        />
      </t-aside>
      <t-content>
        <div ref="containerRef" class="layout-content">
          <LayoutPanels
            :panels="panels"
            :active-view="activeView"
            :default-model="defaultModel"
            @switch-workspace="onSwitchWorkspace"
            @open-file="onOpenFile"
          />
        </div>
      </t-content>
    </t-layout>

    <t-footer
      height="24px"
      style="padding:0!important;background:#007acc"
    >
      <StatusBar :workspace="workspace" />
    </t-footer>
  </t-layout>

  <!-- 切换工作区弹窗 -->
  <DialogWrapper
    :show="showWorkspacePicker"
    title="切换工作区"
    @close="showWorkspacePicker = false"
  >
    <WorkspaceStep @selected="onWorkspaceChanged" />
  </DialogWrapper>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import Sortable from 'sortablejs'
import SideBar from './SideBar.vue'
import StatusBar from './StatusBar.vue'
import LayoutPanels from './LayoutPanels.vue'
import DialogWrapper from '../common/DialogWrapper.vue'
import WorkspaceStep from '../init/WorkspaceStep.vue'

defineProps({ workspace: { type: String, default: '' }, defaultModel: { type: String, default: '' } })
const emit = defineEmits(['workspaceChanged'])
const activeView = ref('file')
const showWorkspacePicker = ref(false)

function onSwitch(v) { activeView.value = v }
function onOpenFile(path) {
  // 由 LayoutPanels 透传给 ViewerBar.openFile
}
function onSwitchWorkspace() {
  showWorkspacePicker.value = true
}

function onWorkspaceChanged() {
  showWorkspacePicker.value = false
  emit('workspaceChanged')
}

const containerRef = ref(null)
const panels = reactive([
  { id: 'resource', w: 260 },  // 侧栏宽度 px
  { id: 'viewer', w: 0 },
  { id: 'interact', w: 360 },
])

onMounted(() => {
  const el = containerRef.value
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
:deep(.t-layout__content) { flex: 1; min-height: 0; min-width: 0; overflow: hidden; display: flex; flex-direction: column; }
.layout-content { display: flex; flex: 1; min-height: 0; min-width: 0; overflow: hidden; align-items: stretch; }
</style>

<style>
/* panel 容器 — 全局 CSS 穿透子组件 LayoutPanels */
.panel { display: flex; flex-direction: column; min-width: 0; min-height: 0; overflow: hidden; border-left: 1px solid #333; }
.panel:first-child { border-left: none; }
.panel.sortable-ghost { opacity: 0.3; }
.panel.sortable-chosen { box-shadow: 0 0 0 2px #409eff inset; }

/* TDesign t-layout__content 必须溢出隐藏 */
.t-layout__content {
  min-height: 0 !important;
  overflow: hidden !important;
}
</style>
