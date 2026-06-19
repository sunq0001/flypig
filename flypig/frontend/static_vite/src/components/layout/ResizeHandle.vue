<!--
ResizeHandle：分栏拖拽手柄组件

为什么做：用户需要像 VS Code 一样拖拽调整各分栏的宽度/高度。
实现方法：监听 mousedown/mousemove/mouseup 事件，支持水平和垂直方向。
实现效果：拖拽时实时更新 modelValue，hover 时手柄高亮。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → layout 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §全局布局
-->
<template>
  <div
    class="resize-handle"
    :class="[direction, { active: dragging }]"
    @mousedown.prevent="startDrag"
  ></div>
</template>

<script setup>
/**
 * @module ResizeHandle：分栏拖拽手柄组件
 * @description 用户需要像 VS Code 一样拖拽调整各分栏的宽度/高度。 监听 mousedown/mousemove/mouseup 事件，支持水平和垂直方向。 拖拽时实时更新 modelValue，hover 时手柄高亮。
 */
import { ref } from 'vue'

const props = defineProps({
  direction: { type: String, default: 'horizontal' }, // horizontal | vertical
  min: { type: Number, default: 36 },
  max: { type: Number, default: Infinity },
  modelValue: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'resize'])
const dragging = ref(false)

function startDrag(e) {
  dragging.value = true
  const startPos = props.direction === 'horizontal' ? e.clientX : e.clientY
  const startSize = props.modelValue

  function onMove(ev) {
    const currentPos = props.direction === 'horizontal' ? ev.clientX : ev.clientY
    const delta = currentPos - startPos
    const newSize = Math.max(props.min, Math.min(props.max, (startSize || 0) + delta))
    emit('update:modelValue', newSize)
    emit('resize', newSize)
  }

  function onUp() {
    dragging.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  document.body.style.cursor = props.direction === 'horizontal' ? 'col-resize' : 'row-resize'
  document.body.style.userSelect = 'none'
}
</script>

<style scoped>
.resize-handle {
  flex-shrink: 0;
  position: relative;
  z-index: 10;
  transition: background 0.1s;
}
.resize-handle.horizontal {
  width: 4px;
  cursor: col-resize;
}
.resize-handle.vertical {
  height: 4px;
  cursor: row-resize;
}
.resize-handle::after {
  content: '';
  position: absolute;
}
.resize-handle.horizontal::after {
  top: 0; bottom: 0; left: -4px; right: -4px;
}
.resize-handle.vertical::after {
  left: 0; right: 0; top: -4px; bottom: -4px;
}
.resize-handle:hover,
.resize-handle.active {
  background: #409eff;
}
</style>
