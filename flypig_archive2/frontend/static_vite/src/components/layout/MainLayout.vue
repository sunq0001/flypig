<!--
MainLayout：三栏布局容器

职责：只编排布局，不做具体业务逻辑。
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
              <ResourceBar v-if="p.id === 'resource'" :activeView="activeView"
                @switchWorkspace="showWorkspacePicker = true" @openFile="onOpenFile" />
              <ViewerBar v-else-if="p.id === 'viewer'" :ref="el => viewerInstance = el" />
              <InteractBar v-else-if="p.id === 'interact'" :model="defaultModel" />
            </div>
          </div>
          <ResizeHandleLR v-if="i < panels.length - 1" :panels="panels" :idx="i" />
        </template>
      </div>
    </div>
    <StatusBar :workspace="workspace" />

    <el-dialog v-model="showWorkspacePicker" title="切换工作区" width="500px" :close-on-click-modal="false">
      <WorkspaceStep @selected="onWorkspaceChanged" />
    </el-dialog>
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
function onSwitch(v) { activeView.value = v }

const showWorkspacePicker = ref(false)
function onWorkspaceChanged() {
  showWorkspacePicker.value = false
  emit('workspaceChanged')
}

let viewerInstance = null
function onOpenFile(path) {
  viewerInstance?.openFile(path)
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
.main-layout { height: 100vh; display: flex; flex-direction: column; background: #1e1e1e; overflow: hidden; }
.layout-row { flex: 1; display: flex; overflow: hidden; }
.layout-body { flex: 1; display: flex; overflow: hidden; min-width: 0; align-items: stretch; }
.panel { display: flex; }
.panel.sortable-ghost { opacity: 0.3; }
.panel.sortable-chosen { box-shadow: 0 0 0 2px #409eff inset; }
.pcontent { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
</style>
