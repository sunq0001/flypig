<!--
EditorPane：查看器面板 — 根据文件类型路由到对应渲染器

为什么做：代码文件用 MonacoEditor，文档文件用 DocxViewer/PdfViewer 等。
实现方法：根据 filePath 后缀选择渲染器，未支持的格式提示不可预览。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → viewer 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="editor-pane" v-if="filePath">
    <BreadcrumbsBar :file-path="filePath" :root-path="workspace" />
    <MonacoEditor v-if="isCodeFile" :value="content" :language="filePath" />
    <div v-else-if="isSupportedDoc" class="pane-placeholder">文档预览（待实现）</div>
    <div v-else class="pane-unsupported">暂不支持预览此文件类型</div>
  </div>
  <div v-else class="pane-placeholder">选择文件以查看</div>
</template>
<script setup>
import { ref, computed, watch } from 'vue'
import { useConfigStore } from '../../stores/config'
import MonacoEditor from './MonacoEditor.vue'
import BreadcrumbsBar from './BreadcrumbsBar.vue'

const props = defineProps({ filePath: { type: String, default: '' } })

const configStore = useConfigStore()
const workspace = computed(() => configStore.workspace)

const content = ref('')
const loading = ref(false)

const codeExtensions = [
  'js','ts','jsx','tsx','vue','py','json','md','html','css','scss','less',
  'yml','yaml','toml','xml','svg','sh','bash','go','rs','java','kt',
  'c','cpp','h','hpp','sql','rb','php','r','txt','gitignore','ini','cfg',
  'env','bat','ps1','conf','log','yaml','dockerfile',
]

const docExtensions = ['docx','pdf','xlsx','pptx']

const ext = computed(() => props.filePath.split('.').pop()?.toLowerCase() || '')
const isCodeFile = computed(() => codeExtensions.includes(ext.value))
const isSupportedDoc = computed(() => docExtensions.includes(ext.value))

async function loadFile(path) {
  if (!path) { content.value = ''; return }
  loading.value = true
  try {
    const res = await fetch(`/api/file?path=${encodeURIComponent(path)}`)
    if (!res.ok) { content.value = '无法读取文件'; return }
    const data = await res.json()
    content.value = data.content || ''
  } catch {
    content.value = '读取文件失败'
  } finally {
    loading.value = false
  }
}

watch(() => props.filePath, loadFile)
</script>
<style scoped>
.editor-pane{width:100%;height:100%;display:flex;flex-direction:column;overflow:hidden}
.editor-pane > :deep(.monaco-editor){flex:1}
.pane-placeholder,.pane-unsupported{height:100%;display:flex;align-items:center;justify-content:center;font-size:14px}
.pane-placeholder{color:#555}
.pane-unsupported{color:#666}
</style>
