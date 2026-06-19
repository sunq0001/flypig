<!--
PdfViewer：PDF 预览 (P1)

为什么做：上传的 PDF 文件需要在浏览器内按指定页码渲染。
实现方法：PDF.js 渲染指定页码为 canvas。
实现效果：用户点 PDF 文件直接看内容，AI 可定位到相关页码。

技术栈：Vue 3 SFC, PDF.js
层&依赖：frontend.presentation → file 组件群（P1 预留）
细节见文档：docs/docs_refactor/tech-stack.md → §PDF 预览
-->
