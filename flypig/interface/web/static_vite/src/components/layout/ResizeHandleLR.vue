<!--
ResizeHandleLR：拖拽手柄，直接调整左右 panel 宽度

拖左 = delta 负，拖右 = delta 正。
requestAnimationFrame 节流避免卡顿。
-->
<template>
  <div class="resize-lr" @mousedown.prevent="startDrag"></div>
</template>

<script setup>
const props = defineProps({
  panels: { type: Array, required: true },
  idx: { type: Number, required: true },
})
let startX = 0, rafId = null, dragStarts = []

function startDrag(e) {
  startX = e.clientX
  dragStarts = []
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function onMove(e) {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = requestAnimationFrame(() => {
    const delta = e.clientX - startX
    if (dragStarts.length === 0) {
      // 用 DOM 实际渲染宽度，包括 w=0 的 flex panel
      const parent = document.querySelector('.layout-body')
      const divs = parent?.querySelectorAll('.panel') || []
      dragStarts = props.panels.map((p, i) => {
        if (p.w > 0) return p.w
        const w = divs[i]?.getBoundingClientRect().width || 200
        return Math.round(w)
      })
    }
    const left = props.panels[props.idx]
    const right = props.panels[props.idx + 1]
    if (!left || !right) { rafId = null; return }
    left.w = Math.max(80, dragStarts[props.idx] + delta)
    right.w = Math.max(80, dragStarts[props.idx + 1] - delta)
    // viewer 始终保持 flex:1（w=0），只调两侧面板宽度
    if (left.id === 'viewer') left.w = 0
    if (right.id === 'viewer') right.w = 0
    rafId = null
  })
}

function onUp() {
  if (rafId) cancelAnimationFrame(rafId)
  dragStarts = []
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  document.removeEventListener('mousemove', onMove)
  document.removeEventListener('mouseup', onUp)
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
