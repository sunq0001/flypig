<!--
TerminalBar：终端栏容器

为什么做：用户在右侧面板需要终端/输出切换，支持折叠。
实现方法：TermBar（标签栏）+ TerminalPanel（终端区域），折叠时仅显示标签栏。
实现效果：可折叠/展开的终端区域，支持多终端切换。

技术栈：Vue 3 SFC
层&依赖：frontend.presentation → terminal 组件群
细节见文档：docs/docs_refactor/frontend-arch.md → §目标目录结构
-->
<template>
  <div class="terminal-bar" :class="{ collapsed }">
    <div class="term-header">
      <div class="term-tabs">
        <span class="term-tab active">
          <span class="dot"></span>
          终端 1
        </span>
        <span class="term-tab">+</span>
      </div>
      <div class="term-actions">
        <span class="term-btn" title="折叠" @click="$emit('toggle')">_</span>
      </div>
    </div>
    <div class="term-body">
      <div class="term-placeholder">终端输出区域</div>
    </div>
  </div>
</template>

<script setup>
/**
 * @module TerminalBar：终端栏容器
 * @description 用户在右侧面板需要终端/输出切换，支持折叠。 TermBar（标签栏）+ TerminalPanel（终端区域），折叠时仅显示标签栏。 可折叠/展开的终端区域，支持多终端切换。
 */
defineProps({
  collapsed: { type: Boolean, default: false }
})
defineEmits(['toggle'])
</script>

<style scoped>
.terminal-bar {
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  border-top: 1px solid #333;
  flex-shrink: 0;
}
.terminal-bar.collapsed {
  height: 28px;
}
.terminal-bar.collapsed .term-body {
  display: none;
}
.term-header {
  height: 28px;
  display: flex;
  align-items: center;
  padding: 0 8px;
  background: #252526;
  border-bottom: 1px solid #1e1e1e;
  flex-shrink: 0;
}
.term-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  overflow: hidden;
}
.term-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 10px;
  height: 24px;
  font-size: 11px;
  color: #666;
  cursor: pointer;
  border-radius: 3px 3px 0 0;
  white-space: nowrap;
}
.term-tab.active {
  background: #1e1e1e;
  color: #ccc;
}
.term-tab:not(.active):hover {
  color: #999;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #4ec9b0;
  flex-shrink: 0;
}
.term-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.term-btn {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #666;
  cursor: pointer;
  border-radius: 3px;
}
.term-btn:hover {
  background: #3c3c3c;
  color: #ccc;
}
.term-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80px;
}
.term-placeholder {
  color: #555;
  font-size: 13px;
}
</style>
