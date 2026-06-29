<!--
ResizeHandleLR：拖拽手柄，emit resize(delta)

拖左 = delta 负，拖右 = delta 正。
requestAnimationFrame 节流避免卡顿。
-->
<template>
  <div class="resize-lr" @mousedown.prevent="startDrag"></div>
</template>

<script setup>
const emit = defineEmits(['resize'])
let startX = 0, rafId = null

function startDrag(e) {
  startX = e.clientX
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function onMove(e) {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = requestAnimationFrame(() => {
    emit('resize', e.clientX - startX)
    rafId = null
  })
}

function onUp() {
  if (rafId) cancelAnimationFrame(rafId)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onMove)
  document.removeEventListener('mouseup', onUp)
  emit('resize', 0)
}
</script>

<style scoped>
.resize-lr {
  width: 0; flex-shrink: 0;
  position: relative; z-index: 10;
}
.resize-lr::before {
  content: ''; position: absolute; top: 0; bottom: 0;
  left: -6px; right: -6px; cursor: col-resize;
}
.resize-lr:hover::before { background: #409eff; }
</style>
