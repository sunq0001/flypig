<!--
FileBar：文件标签栏（类似 VS Code 多标签）

为什么做：用户打开多个文件后需要在文件间切换，类似 VS Code 的标签页。
实现方法：接收 files 数组和 activeFile，支持选择/关闭标签。
实现效果：多文件切换直观，标签栏紧凑不占空间。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → viewer 组件群
-->
<template>
  <div class="file-bar">
    <div class="tab-list">
      <div
        v-for="f in files" :key="f.path"
        class="tab" :class="{ active: f.path === activeFile }"
        @click="$emit('selectFile', f.path)"
        @mousedown.middle.prevent="$emit('closeFile', f.path)"
      >
        <span class="tab-name">{{ f.name }}</span>
        <span class="tab-close" @click.stop="$emit('closeFile', f.path)">×</span>
      </div>
    </div>
  </div>
</template>
<script setup>
defineProps({ files: { type: Array, default: () => [] }, activeFile: { type: String, default: '' } })
defineEmits(['selectFile', 'closeFile'])
</script>
<style scoped>
.file-bar{height:35px;display:flex;align-items:center;background:#252526;border-bottom:1px solid #1e1e1e;flex-shrink:0;overflow:hidden}
.tab-list{display:flex;align-items:stretch;height:100%;overflow-x:auto}
.tab-list::-webkit-scrollbar{height:0}
.tab{display:flex;align-items:center;gap:6px;padding:0 12px;height:100%;font-size:12px;color:#888;cursor:pointer;border-right:1px solid #1e1e1e;white-space:nowrap;flex-shrink:0;transition:background .1s}
.tab.active{color:#ccc;background:#1e1e1e;border-bottom:2px solid #409eff;margin-bottom:-1px}
.tab:hover{color:#ccc;background:#2a2a2a}
.tab-close{font-size:14px;line-height:1;color:#555;padding:2px;border-radius:3px;margin-left:2px}
.tab-close:hover{background:#555;color:#fff}
</style>
