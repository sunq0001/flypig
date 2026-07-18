<!--
ResourceBar：左侧资源栏容器

为什么做：用户需要在文件树、能力管理、统计等资源面板间切换，由 ActivityBar 控制。
实现方法：📁 切换工作区使用 TDesign Dropdown 组件，VSCode 风格的「文件」菜单：
          - 主菜单：浏览其他 / 清除最近
          - 最近打开的工作区（子菜单，带路径）
实现效果：点击文件资源管理器标题旁的 📁 图标弹出菜单，hover 最近工作区展开子菜单。
技术栈：Vue 3 SFC, TDesign Dropdown
层&依赖：frontend.presentation → resource 组件群
-->

<template>
  <div class="resource-bar">
    <div class="bar-header">
      <template v-if="activeView === 'file'">
        <t-dropdown
          :options="dropdownOptions"
          :hide-after-item-click="true"
          :max-column-width="420"
          :min-column-width="200"
          trigger="click"
          placement="bottom-left"
          :popup-props="{
            zIndex: 4000,
            delay: 250,
          }"
          @click="onDropdownClick"
        >
          <div class="header-clickable">
            <span>{{ activeLabel }}</span>
            <span class="btn-workspace">📁</span>
          </div>
        </t-dropdown>
      </template>
      <span v-else>{{ activeLabel }}</span>
    </div>
    <div class="bar-body">
      <FileTreeBar
        v-if="activeView === 'file'"
        @switch-workspace="$emit('switch-workspace')"
        @open-file="p => $emit('open-file', p)"
      />
      <McpBar v-if="activeView === 'mcp'" />
      <StatsBar v-if="activeView === 'stats'" />
    </div>
  </div>
</template>

<script setup>
/**
 * @module ResourceBar — 左侧资源栏（含 VSCode 风格工作区下拉菜单）
 * @description VSCode 风格的两列下拉菜单：左侧主命令，右侧「最近工作区」子菜单。
 */
import { computed } from 'vue'
import { useConfigStore } from '@/stores/config'
import FileTreeBar from '../resource/FileTreeBar.vue'
import McpBar from '../resource/McpBar.vue'
import StatsBar from '../resource/StatsBar.vue'

const emit = defineEmits(['switch-workspace', 'open-file'])

const props = defineProps({ activeView: { type: String, default: 'file' } })

const configStore = useConfigStore()

const activeLabel = computed(() =>
  ({ file: '文件资源管理器', mcp: '能力', stats: '统计' }[props.activeView] || '文件资源管理器'),
)

// 渲染菜单项：去掉之前的多 wrapper（让 TDesign Dropdown 自带样式生效）
const dropdownOptions = computed(() => {
  const items = []

  // 浏览其他
  items.push({
    content: '浏览其他',
    value: 'browse',
  })

  // 最近打开的工作区（子菜单，去重 + 倒序）
  const seen = new Set()
  const recent = (configStore.recent_workspaces || [])
    .filter((ws) => {
      if (seen.has(ws)) return false
      seen.add(ws)
      return true
    })
    .reverse()
  items.push({
    content: '最近打开的工作区',
    value: '__recent_label__',
    children: recent.length > 0
      ? recent.map((ws) => ({
          content: ws,
          value: ws,
        }))
      : [{ content: '（无最近打开的工作区）', value: '__empty__', disabled: true }],
  })

  // 分隔 + 清除最近
  if (recent.length > 0) {
    items.push({ divider: true })
    items.push({
      content: '清除最近打开的工作区',
      value: 'clear',
    })
  }

  return items
})

function onDropdownClick(optionItem) {
  const value = optionItem.value
  if (value === 'browse') {
    emit('switch-workspace')
  } else if (value === 'clear') {
    configStore.clearRecent()
  } else if (value && !value.startsWith('__') && value !== '') {
    // 最近工作区路径（value 就是路径字符串），跳过占位符
    configStore.setWorkspace(value)
  }
}
</script>

<style scoped>
.resource-bar {
  width: 100%;
  height: 100%;
  background: #252526;
  color: #ccc;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #1e1e1e;
}
.bar-header {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px 0 16px;
  font-size: 12px;
  font-weight: 600;
  color: #aaa;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #1e1e1e;
  flex-shrink: 0;
}
.header-clickable {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  width: 100%;
  justify-content: space-between;
}
.btn-workspace {
  background: none;
  border: none;
  color: #aaa;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 3px;
  line-height: 1;
}
.btn-workspace:hover {
  color: #e0e0e0;
  background: #3c3c3c;
}
.bar-body {
  flex: 1;
  overflow-y: auto;
}
</style>
