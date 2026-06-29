<!--
ExcelViewer：Excel 预览 (P1)

为什么做：上传的 .xlsx 文件需要在浏览器内预览，而不是下载到本地再打开。
实现方法：SheetJS (xlsx) 在浏览器内读取 workbook，按 AI 标注行列渲染为表格。
实现效果：用户点 Excel 文件直接看内容，不离开浏览器。

技术栈：Vue 3 SFC, SheetJS (xlsx)
层&依赖：frontend.presentation → file 组件群（P1 预留）
细节见文档：docs/docs_refactor/tech-stack.md → §Excel 预览
-->
<template>
  <div class="excelViewer">
    <!-- TODO: implement -->
  </div>
</template>

<script setup>
/**
 * ExcelViewer -- TODO: implement component logic
 */
</script>

<style scoped>
.excelViewer { }
</style>
