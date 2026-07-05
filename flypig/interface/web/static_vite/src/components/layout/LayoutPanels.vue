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
