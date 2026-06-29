<!--
MonacoEditor：代码编辑器
使用 Monaco Editor 原生 worker 加载，支持语法高亮。
-->

<template>
  <div ref="container" class="monaco-editor"></div>
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as monaco from 'monaco-editor'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker'
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker'
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker'

self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') return new jsonWorker()
    if (label === 'css' || label === 'scss' || label === 'less') return new cssWorker()
    if (label === 'html' || label === 'handlebars' || label === 'razor') return new htmlWorker()
    if (label === 'typescript' || label === 'javascript') return new tsWorker()
    return new editorWorker()
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
    breadcrumbs: { enabled: false },
    stickyScroll: { enabled: true },
    folding: true,
    bracketPairColorization: { enabled: true },
    guides: { indentation: true, bracketPairs: true },
    renderLineHighlight: 'all',
    matchBrackets: 'always',
    cursorBlinking: 'smooth', smoothScrolling: true,
    tabSize: 2, detectIndentation: true,
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
