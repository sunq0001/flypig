<!--
LocalModelDialog：本地模型选择弹窗

状态：
  1. Ollama 未安装 → 引导下载
  2. Ollama 运行中无模型 → 推荐列表 + 下载
  3. Ollama 运行中有模型 → 模型列表，点击选中
-->
<template>
  <t-dialog
    :visible="visible"
    width="420px"
    :header="false"
    :footer="false"
    :close-on-overlay-click="true"
    :close-btn="true"
    :dialog-style="{ background: '#252526' }"
    @update:visible="$emit('close')"
    @close="$emit('close')"
  >
    <!-- 状态1: Ollama 未安装 -->
    <div
      v-if="!loading && !status.running"
      class="ld-body"
    >
      <div class="ld-icon-wrap">
        💻
      </div>
      <div class="ld-title">
        本地模型
      </div>
      <div class="ld-desc">
        未检测到 Ollama，本地模型需要 Ollama 支持
      </div>
      <a
        href="https://ollama.com/download"
        target="_blank"
        class="ld-btn"
      >下载 Ollama</a>
      <div class="ld-hint">
        安装完成后刷新页面即可使用
      </div>
    </div>

    <!-- 状态2: Ollama 运行中，无模型 -->
    <div
      v-else-if="!loading && status.running && !status.installed?.length"
      class="ld-body"
    >
      <div class="ld-status-bar">
        <span class="ld-dot ld-dot-green" />
        <span class="ld-status-text">Ollama 已就绪</span>
      </div>
      <div class="ld-nomodel-desc">
        <p>尚未安装任何模型。</p>
        <p>请在终端运行：</p>
        <code class="ld-code">ollama pull qwen2.5:1.5b</code>
        <p>安装完成后刷新此页面即可选择。</p>
      </div>
    </div>

    <!-- 状态3: Ollama 运行中，有模型 -->
    <div
      v-else-if="!loading && status.running && status.installed?.length"
      class="ld-body"
    >
      <div class="ld-status-bar">
        <span class="ld-dot ld-dot-green" />
        <span class="ld-status-text">已安装 {{ status.installed.length }} 个本地模型</span>
      </div>
      <div class="ld-model-list">
        <div
          v-for="m in status.installed"
          :key="m"
          :class="['ld-model-item', { 'ld-model-item-active': selectedModel === m }]"
          @click="selectedModel = m"
        >
          <span :class="['ld-radio', { 'ld-radio-checked': selectedModel === m }]" />
          <span class="ld-model-name">{{ m }}</span>
          <span class="ld-model-badge">就绪</span>
        </div>
      </div>
      <div class="ld-actions">
        <t-button @click="$emit('close')">
          取消
        </t-button>
        <t-button
          theme="primary"
          :disabled="!selectedModel"
          @click="confirmSelect"
        >
          确认选择
        </t-button>
      </div>
    </div>

    <!-- 加载中 -->
    <div
      v-else
      class="ld-body ld-loading"
    >
      <span>检测中...</span>
    </div>
  </t-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { getLocalModels } from '@/utils/api'

const props = defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'select'])

const loading = ref(false)
const status = ref({ running: false, installed: [] })
const selectedModel = ref('')

async function _onVisibleChange(v) {
  if (!v) return
  loading.value = true
  try {
    status.value = await getLocalModels()
    if (status.value.installed?.length) {
      selectedModel.value = status.value.installed[0]
    }
  } catch {
    status.value = { running: false, installed: [] }
  } finally {
    loading.value = false
  }
}
watch(() => props.visible, _onVisibleChange)

function confirmSelect() {
  if (selectedModel.value) {
    emit('select', selectedModel.value)
    emit('close')
  }
}
</script>

<style scoped>
.ld-body {
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.ld-icon-wrap {
  font-size: 36px;
  margin-bottom: 8px;
}
.ld-title {
  font-size: 14px;
  color: #e5e5e5;
  font-weight: 600;
  margin-bottom: 6px;
}
.ld-desc {
  font-size: 12px;
  color: #999;
  margin-bottom: 16px;
  text-align: center;
}
.ld-btn {
  display: inline-block;
  padding: 6px 24px;
  background: #409eff;
  color: #fff;
  border-radius: 4px;
  font-size: 13px;
  text-decoration: none;
  margin-bottom: 10px;
  transition: background 0.15s;
}
.ld-btn:hover { background: #66b1ff; }
.ld-hint {
  font-size: 11px;
  color: #666;
}
/* 状态条 */
.ld-status-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  margin-bottom: 12px;
}
.ld-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.ld-dot-green { background: #52c41a; }
.ld-status-text {
  font-size: 12px;
  color: #bbb;
}
.ld-subtitle {
  align-self: flex-start;
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}
/* 推荐卡片 */
.ld-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 6px 8px;
  border-radius: 4px;
  margin-bottom: 4px;
  transition: background 0.1s;
}
.ld-card:hover { background: #3c3c3c; }
.ld-card-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.ld-card-name { color: #ccc; font-size: 12px; white-space: nowrap; }
.ld-card-size { color: #888; font-size: 10px; white-space: nowrap; }
.ld-card-desc { color: #666; font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ld-footnote {
  align-self: flex-start;
  margin-top: 8px;
  font-size: 11px;
  color: #666;
}
/* 无模型提示 */
.ld-nomodel-desc {
  align-self: flex-start;
  font-size: 12px;
  color: #999;
  line-height: 1.6;
}
.ld-nomodel-desc p { margin: 4px 0; }
.ld-code {
  display: inline-block;
  background: #1e1e1e;
  color: #52c41a;
  padding: 4px 10px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  margin: 6px 0;
}
/* 模型列表 */
.ld-model-list {
  width: 100%;
  margin-bottom: 12px;
}
.ld-model-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.1s;
}
.ld-model-item:hover { background: #3c3c3c; }
.ld-model-item-active { background: rgba(64, 158, 255, 0.12); }
.ld-radio {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid #555;
  flex-shrink: 0;
  transition: all 0.15s;
}
.ld-radio-checked {
  border-color: #409eff;
  background: #409eff;
  box-shadow: inset 0 0 0 3px #252526;
}
.ld-model-name { color: #e5e5e5; font-size: 12px; flex: 1; }
.ld-model-badge {
  font-size: 10px;
  color: #52c41a;
  background: rgba(82, 196, 26, 0.1);
  padding: 1px 6px;
  border-radius: 3px;
}
/* 操作按钮 */
.ld-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  width: 100%;
  border-top: 1px solid #333;
  padding-top: 12px;
}
.ld-loading {
  color: #999;
  font-size: 13px;
  padding: 24px 0;
}
</style>
