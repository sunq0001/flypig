<!--
EditorPane：查看器面板 — 根据文件类型路由到对应渲染器
-->

<template>
  <div class="editor-pane" v-if="filePath">
    <BreadcrumbsBar :file-path="filePath" :root-path="workspace" />
    <MonacoEditor v-if="isCodeFile" :value="content" :language="filePath" />
    <div v-else-if="isImage" class="image-viewer">
      <img :src="imageDataUrl || imageSrc" :alt="filePath" @load="onImageLoad" @error="onImageError" />
    </div>
    <div v-else-if="isSupportedDoc" class="pane-placeholder">文档预览（待实现）</div>
    <div v-else class="pane-unsupported">暂不支持预览此文件类型</div>
  </div>
  <div v-else class="pane-placeholder">选择文件以查看</div>
</template>
<script setup>
import { ref, computed, watch } from 'vue'
import { useConfigStore } from '../../stores/config'
import { readFile } from '../../utils/api'
import MonacoEditor from './MonacoEditor.vue'
import BreadcrumbsBar from './BreadcrumbsBar.vue'

const props = defineProps({ filePath: { type: String, default: '' } })

const configStore = useConfigStore()
const workspace = computed(() => configStore.workspace)

const content = ref('')
const loading = ref(false)
const imageDataUrl = ref('')

const codeExtensions = [
  'js','ts','jsx','tsx','vue','py','json','md','html','css','scss','less',
  'yml','yaml','toml','xml','svg','sh','bash','go','rs','java','kt',
  'c','cpp','h','hpp','sql','rb','php','r','txt','gitignore','ini','cfg',
  'env','bat','ps1','conf','log','yaml','dockerfile',
]

const docExtensions = ['docx','pdf','xlsx','pptx']
const imageExtensions = ['png','jpg','jpeg','gif','svg','webp','ico','bmp']

const ext = computed(() => props.filePath.split('.').pop()?.toLowerCase() || '')
const isCodeFile = computed(() => codeExtensions.includes(ext.value))
const isImage = computed(() => imageExtensions.includes(ext.value))
const isSupportedDoc = computed(() => docExtensions.includes(ext.value))
const isElectron = typeof window !== 'undefined' && window.electronAPI

const imageSrc = computed(() => {
  if (!props.filePath || !isImage.value || isElectron) return ''
  return `/api/file?path=${encodeURIComponent(props.filePath)}`
})

async function loadFile(path) {
  if (!path) { content.value = ''; imageDataUrl.value = ''; return }
  loading.value = true
  try {
    const result = await readFile(path)
    if (result.type === 'image' && isElectron) {
      imageDataUrl.value = `data:image/${result.ext};base64,${result.data}`
    } else if (result.type === 'text') {
      content.value = result.content || ''
    } else {
      content.value = '无法读取文件'
    }
  } catch {
    content.value = '读取文件失败'
  } finally {
    loading.value = false
  }
}

function onImageLoad() { /* 图片加载成功 */ }
function onImageError(e) {
  e.target.style.display = 'none'
  e.target.parentElement.innerHTML = '<span class="pane-unsupported">图片加载失败</span>'
}

watch(() => props.filePath, loadFile)
</script>
<style scoped>
.editor-pane{width:100%;height:100%;display:flex;flex-direction:column;overflow:hidden}
.editor-pane > :deep(.monaco-editor){flex:1}
.pane-placeholder,.pane-unsupported{height:100%;display:flex;align-items:center;justify-content:center;font-size:14px}
.pane-placeholder{color:#555}
.pane-unsupported{color:#666}
.image-viewer{flex:1;display:flex;align-items:center;justify-content:center;background:#1a1a1a;overflow:auto;padding:16px}
.image-viewer img{max-width:100%;max-height:100%;object-fit:contain;border-radius:4px}
</style>
