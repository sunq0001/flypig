<!--
DocxViewer：Word 预览 (P1)

为什么做：上传的 .docx 文件需要在浏览器内渲染为 HTML 预览。
实现方法：mammoth.js 转换 docx → HTML 渲染。
实现效果：用户点 Word 文件直接看内容，AI 定位结论段落。

技术栈：Vue 3 SFC, mammoth.js
层&依赖：frontend.presentation → file 组件群（P1 预留）
细节见文档：docs/docs_refactor/tech-stack.md → §Word 预览
-->
