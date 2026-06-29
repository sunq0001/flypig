<!--
FileTreeBar：资源栏文件树组件

为什么做：用户需要直观地查看工作区目录结构，在资源栏中展示文件树。
实现方法：无工作区时显示欢迎引导，有工作区时渲染 FileTree。
实现效果：首次打开引导选工作区，之后直接显示文件树。

技术栈：Vue 3 SFC, 递归组件
层&依赖：frontend.presentation → resource 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="file-tree-bar">
    <!-- 无工作区 → 欢迎引导 -->
    <div v-if="!workspace" class="welcome-area">
      <div class="welcome-icon">📂</div>
      <p class="welcome-title">选择工作区</p>
      <p class="welcome-desc">选择一个目录作为 AI 助手的工作空间</p>
      <button class="btn-open" @click="$emit('switchWorkspace')">打开工作区</button>
      <div v-if="recentList.length > 0" class="recent-list">
        <div class="recent-label">最近使用</div>
        <div v-for="(ws, idx) in recentList" :key="idx" class="recent-item" @click="openRecent(ws)">
          <span class="recent-path">{{ ws }}</span>
        </div>
      </div>
    </div>

    <!-- 有工作区 → 文件树 -->
    <FileTree v-else :root-path="workspace" @switch-workspace="$emit('switchWorkspace')" @open-file="p => $emit('openFile', p)" />
  </div>
</template>
<script setup>
/**
 * @module FileTreeBar — 文件树组件（含工作区选择引导）
 * @description 无工作区时显示欢迎引导，有工作区时渲染 FileTree。
 */
import { computed } from 'vue'
import { useConfigStore } from '../../stores/config'
import FileTree from './FileTree.vue'

defineEmits(['switchWorkspace', 'openFile'])
const configStore = useConfigStore()
const workspace = computed(() => configStore.workspace)
const recentList = computed(() => configStore.recent_workspaces)

async function openRecent(path) {
  await configStore.setWorkspace(path)
}
</script>
<style scoped>
.file-tree-bar{height:100%}
.welcome-area{display:flex;flex-direction:column;align-items:center;padding:32px 20px;gap:12px;text-align:center}
.welcome-icon{font-size:40px;opacity:.5}
.welcome-title{font-size:14px;font-weight:600;color:#888;margin:0}
.welcome-desc{font-size:11px;color:#666;margin:0;line-height:1.5}
.btn-open{background:#409eff;color:#fff;border:none;padding:8px 20px;border-radius:6px;font-size:13px;cursor:pointer;transition:background .15s}
.btn-open:hover{background:#337ecc}
.recent-list{margin-top:8px;width:100%;display:flex;flex-direction:column;gap:2px}
.recent-label{font-size:10px;color:#555;text-transform:uppercase;letter-spacing:.5px;padding:4px 0}
.recent-item{padding:6px 10px;border-radius:4px;cursor:pointer;transition:background .15s}
.recent-item:hover{background:#333}
.recent-path{font-size:11px;color:#999;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block}
</style>
