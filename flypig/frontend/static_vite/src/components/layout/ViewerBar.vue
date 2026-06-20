<!--
ViewBar：中间查看栏容器

为什么做：用户在中间区域查看文件内容，需要文件标签栏 + 编辑器/预览区。
实现方法：FileBar（顶部标签）+ 查看区域，后续可扩展为 MonacoEditor 或文件预览组件。
实现效果：打开文件后中间区域显示文件内容，标签可切换多个打开文件。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → viewer 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="view-bar">
    <FileBar />
    <div class="view-body">
      <div class="view-placeholder">选择文件以查看</div>
    </div>
  </div>
</template>
<script setup>
/**
 * @module ViewBar：中间查看栏容器
 * @description 用户在中间区域查看文件内容，需要文件标签栏 + 编辑器/预览区。 FileBar（顶部标签）+ 查看区域，后续可扩展为 MonacoEditor 或文件预览组件。 打开文件后中间区域显示文件内容，标签可切换多个打开文件。
 */
import FileBar from '../viewer/FileBar.vue'
</script>
<style scoped>
.view-bar{width:100%;height:100%;display:flex;flex-direction:column;overflow:hidden;border-left:1px solid #333}
.view-body{flex:1;display:flex;align-items:center;justify-content:center;color:#555;font-size:14px}
</style>
