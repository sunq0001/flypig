<!--
FileBar：文件标签栏

为什么做：用户打开多个文件后需要在文件间切换，类似 VS Code 的标签页。
实现方法：水平标签列表，当前文件高亮，支持关闭标签。
实现效果：多文件切换直观，标签栏紧凑不占空间。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → viewer 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="file-bar">
    <div class="tab-list">
      <div class="tab active"><span class="tab-name">无标题</span><span class="tab-close">×</span></div>
    </div>
  </div>
</template>
<style scoped>
.file-bar{height:35px;display:flex;align-items:center;background:#252526;border-bottom:1px solid #1e1e1e;flex-shrink:0;overflow:hidden}
.tab-list{display:flex;align-items:stretch;height:100%;overflow-x:auto}
.tab-list::-webkit-scrollbar{height:0}
.tab{display:flex;align-items:center;gap:6px;padding:0 12px;height:100%;font-size:12px;color:#888;cursor:pointer;border-right:1px solid #1e1e1e;white-space:nowrap;flex-shrink:0}
.tab.active{color:#ccc;background:#1e1e1e;border-bottom:1px solid #1e1e1e;margin-bottom:-1px}
.tab:hover{color:#ccc}
.tab-close{font-size:14px;line-height:1;color:#555;padding:2px;border-radius:3px}
.tab-close:hover{background:#3c3c3c;color:#ccc}
</style>
