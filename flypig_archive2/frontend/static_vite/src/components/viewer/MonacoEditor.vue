<!--
MonacoEditor：代码编辑器

为什么做：用户需要一个专业的代码编辑器来查看和编辑 AI 修改的文件。
实现方法：Monaco Editor（VS Code 同款），Vue wrapper，支持 readonly 模式/语法高亮。
实现效果：编辑体验与 VS Code 一致。

技术栈：Vue 3 SFC, Monaco Editor
层&依赖：frontend.presentation → viewer 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div ref="container" class="monaco-editor"></div>
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as monaco from 'monaco-editor'

// Monaco Worker: 用 CDN 方式加载，避免 Vite worker 打包问题
const WORKER_CDN = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.55.1/min/vs'
self.MonacoEnvironment = {
  getWorkerUrl: (_, label) => {
    if (label === 'json') return `${WORKER_CDN}/language/json/json.worker.js`
    if (label === 'css' || label === 'scss' || label === 'less') return `${WORKER_CDN}/language/css/css.worker.js`
    if (label === 'html' || label === 'handlebars' || label === 'razor') return `${WORKER_CDN}/language/html/html.worker.js`
    if (label === 'typescript' || label === 'javascript') return `${WORKER_CDN}/language/typescript/typescript.worker.js`
    return `${WORKER_CDN}/editor/editor.worker.js`
  },
}

const props = defineProps({
  value: { type: String, default: '' },
  language: { type: String, default: 'plaintext' },
  readonly: { type: Boolean, default: true },
})

const container = ref(null)
let editor = null
let model = null

function getLanguage(filename) {
  const map = {
    js: 'javascript', ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
    vue: 'html', py: 'python', json: 'json', md: 'markdown',
    html: 'html', css: 'css', scss: 'scss', less: 'less',
    yml: 'yaml', yaml: 'yaml', toml: 'ini',
    xml: 'xml', svg: 'xml', sh: 'shell', bash: 'shell',
    go: 'go', rs: 'rust', java: 'java', kt: 'kotlin',
    c: 'c', cpp: 'cpp', h: 'c', hpp: 'cpp',
    sql: 'sql', rb: 'ruby', php: 'php', r: 'r',
    txt: 'plaintext', gitignore: 'plaintext',
  }
  return map[filename.split('.').pop()?.toLowerCase()] || 'plaintext'
}

function createModel(value, filePath) {
  const uri = monaco.Uri.parse(`file:///${filePath.replace(/\\/g, '/')}`)
  return monaco.editor.createModel(value || '', getLanguage(filePath), uri)
}

onMounted(() => {
  model = createModel(props.value, props.language)
  editor = monaco.editor.create(container.value, {
    model, readOnly: props.readonly, theme: 'vs-dark',
    fontSize: 13, fontFamily: "'Cascadia Code', 'Fira Code', Consolas, monospace",
    fontLigatures: true, lineNumbers: 'on',
    minimap: { enabled: false }, scrollBeyondLastLine: false,
    automaticLayout: true, wordWrap: 'on', padding: { top: 8 },

    // === 导航（面包屑由外部 BreadcrumbsBar 组件处理） ===
    breadcrumbs: { enabled: false },
    stickyScroll: { enabled: true },
    folding: true, foldingHighlight: true, foldingStrategy: 'indentation',

    // === 视觉增强 ===
    bracketPairColorization: { enabled: true },
    guides: { indentation: true, bracketPairs: true },
    renderLineHighlight: 'all',
    matchBrackets: 'always',
    occurrencesHighlight: 'single',
    selectionHighlight: true,
    colorDecorators: true,
    renderWhitespace: 'boundary',
    unicodeHighlight: { ambiguousCharacters: true, invisibleCharacters: true },

    // === 代码智能 ===
    codeLens: true,
    inlayHints: { enabled: 'on' },
    hover: { enabled: true, delay: 300 },
    quickSuggestions: { other: true, comments: false, strings: true },
    parameterHints: { enabled: true, cycle: true },
    autoClosingBrackets: 'always',
    autoIndent: 'full',
    formatOnPaste: true,
    linkedEditing: true,

    // === 编辑体验 ===
    cursorBlinking: 'smooth', smoothScrolling: true,
    tabSize: 2, detectIndentation: true,
    dragAndDrop: true,
    emptySelectionClipboard: true,
  })
})

watch(() => props.value, (val) => {
  if (!editor) return
  const current = editor.getValue()
  if (val !== current) {
    model?.setValue(val || '')
  }
})

watch(() => props.language, (lang) => {
  if (!editor) return
  const newLang = getLanguage(lang)
  const oldModel = editor.getModel()
  if (oldModel?.getLanguageId() !== newLang || oldModel?.uri?.path !== lang) {
    model?.dispose()
    model = createModel(editor.getValue(), lang)
    editor.setModel(model)
  }
})

onBeforeUnmount(() => {
  model?.dispose()
  editor?.dispose()
})
</script>
<style scoped>
.monaco-editor{width:100%;height:100%}
</style>
