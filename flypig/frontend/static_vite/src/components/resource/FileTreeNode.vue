<!--
FileTreeNode：树节点

为什么做：文件树中的每个节点（目录或文件）需要展开/折叠/图标/上下文菜单。
实现方法：Vue 3 递归渲染，目录节点有展开/折叠图标，文件节点显示文件类型图标。点击节点触发事件。
实现效果：文件树交互流畅，目录可展开/折叠。

技术栈：Vue 3 SFC, 递归渲染
层&依赖：frontend.presentation → sidebar 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="fileTreeNode">
    <!-- TODO: implement -->
  </div>
</template>

<script setup>
/**
 * FileTreeNode -- TODO: implement component logic
 */
</script>

<style scoped>
.fileTreeNode { }
</style>
