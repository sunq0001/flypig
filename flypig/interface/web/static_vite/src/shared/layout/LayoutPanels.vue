<!-- LayoutPanels：可拖拽排序的三栏面板容器 -->
<template>
  <template
    v-for="(p, i) in panels"
    :key="p.id"
  >
    <div
      class="panel"
      :style="panelStyle(p)"
      :data-panel-id="p.id"
    >
      <span
        class="drag-handle"
        title="拖拽交换面板位置"
      >⋮⋮</span>
      <ResourceBar
        v-if="p.id === 'resource'"
        :active-view="activeView"
        @switch-workspace="$emit('switch-workspace')"
        @open-file="onOpenFile"
      />
      <ViewerBar
        v-else-if="p.id === 'viewer'"
        :ref="el => { if (el) viewerRef = el }"
      />
      <InteractBar
        v-else-if="p.id === 'interact'"
        :model="defaultModel"
      />
    </div>
    <ResizeHandleLR
      v-if="i < panels.length - 1"
      :panels="panels"
      :idx="i"
    />
  </template>
</template>

<script setup>
import { ref } from 'vue'
import ResourceBar from './ResourceBar.vue'
import ViewerBar from './ViewerBar.vue'
import InteractBar from './InteractBar.vue'
import ResizeHandleLR from './ResizeHandleLR.vue'

defineProps({ panels: { type: Array, default: () => [] }, activeView: { type: String, default: '' }, defaultModel: { type: String, default: '' } })
defineEmits(['switch-workspace', 'open-file'])

const viewerRef = ref(null)

function onOpenFile(path) { viewerRef.value?.openFile(path) }

function panelStyle(p) {
  if (p.id === 'viewer' && p.w <= 0) return { flex: '1', minWidth: 80 }
  return { width: Math.max(80, p.w) + 'px', flexShrink: 0 }
}
</script>

<style scoped>
.drag-handle {
  position: absolute;
  top: 10px;
  right: 0;
  cursor: grab;
  font-size: 14px;
  color: #888;
  padding: 3px 9px;
  border-radius: 0 0 0 4px;
  z-index: 10;
  line-height: 1;
  user-select: none;
  -webkit-user-select: none;
}
.drag-handle:hover {
  color: #eee;
  background: #3c3c3c;
}
.drag-handle:active {
  cursor: grabbing;
}
</style>
