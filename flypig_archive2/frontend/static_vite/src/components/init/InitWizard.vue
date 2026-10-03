<!--
InitWizard — 工作区初始化向导

注意事项：
- InitWizard 只有一步：选择/创建工作区（WorkspaceStep）
- 不包含模型选择和 API Key 输入——模型选择和 API Key 配置在聊天界面的 model-bar 中处理
- workspace 选择后 POST /api/config/workspace 持久化，下次打开直接进聊天界面
-->

<template>
  <div class="init-wizard">
    <div class="wizard-container">
      <div class="wizard-header">
        <div class="wizard-logo">🐷</div>
        <h1>欢迎使用 FlyPig Agent</h1>
        <p class="wizard-desc">
          请选择一个工作目录，AI 助手将在此目录中执行文件操作和命令。
          你可以选择现有项目目录，或创建一个新的空目录。
        </p>
      </div>

      <div class="wizard-body">
        <WorkspaceStep @selected="onSelected" />
      </div>

      <div class="wizard-footer">
        <p class="hint">选择一个目录后即可开始使用</p>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * @module InitWizard — 工作区初始化向导
 * @description InitWizard — 工作区初始化向导
 */
import WorkspaceStep from './WorkspaceStep.vue'

const emit = defineEmits(['done'])

function onSelected() {
  emit('done')
}
</script>

<style scoped>
.init-wizard {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.wizard-container {
  width: 100%;
  max-width: 560px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.wizard-header {
  padding: 32px 32px 0;
  text-align: center;
}

.wizard-logo {
  font-size: 48px;
  margin-bottom: 12px;
}

.wizard-header h1 {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.wizard-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.6;
  margin-bottom: 0;
}

.wizard-body {
  padding: 24px 32px;
}

.wizard-footer {
  padding: 0 32px 24px;
  text-align: center;
}

.hint {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
