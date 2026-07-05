<!--
MonacoEditor：代码编辑器
使用 Monaco Editor 原生 worker 加载，支持语法高亮。
-->

<template>
  <div
    ref="container"
    class="monaco-editor"
  />
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { monaco } from '@/lib/monaco-setup'
import { getLanguage as getMonacoLang } from '@/config/editor-languages'
// worker 注册移至 lib/monaco-setup.js，统一管理

const props = defineProps({
  value: { type: String, default: '' },
  language: { type: String, default: 'plaintext' },
  readonly: { type: Boolean, default: true },
})

const container = ref(null)
let editor = null
let model = null

function getLanguage(filename) {
  const ext = filename.split('.').pop()?.toLowerCase()
  return getMonacoLang(ext)
}

function createModel(value, filePath) {
  const uri = monaco.Uri.parse(`file:///${filePath.replace(/\\/g, '/')}`)
  return monaco.editor.createModel(value || '', getLanguage(filePath), uri)
}

onMounted(() => {
  model = createModel(props.value, props.language)
  editor = monaco.editor.create(container.value, {
    model, readOnly: props.readonly, theme: 'vs-dark',
    fontSize: 13,  // 编辑器字号 px
    fontFamily: "'Cascadia Code', 'Fira Code', Consolas, monospace",
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
