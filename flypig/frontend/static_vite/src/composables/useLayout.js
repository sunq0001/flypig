/**
 * 布局状态管理 composable
 * @module useLayout
 * @description 管理三栏布局的宽度、翻转、编辑器/终端比例
 *
 * 为什么做：用户需要像 VS Code 一样拖拽调整布局，支持左右翻转。
 * 实现方法：ref 响应式状态 + computed 面板顺序，支持鼠标拖拽回调。
 * 实现效果：侧边栏 260px、对话面板 360px 初始宽度，可拖拽范围 180~600px。
 *
 * @returns {Object} layout state & methods
 * @property {number} sidebarWidth - 侧边栏宽度 px，范围 180~500
 * @property {number} chatWidth - 对话面板宽度 px，范围 280~600
 * @property {number} editorRatio - 编辑器占总 Center 高度比例，默认 0.55
 * @property {boolean} isFlipped - 是否翻转布局
 * @property {string[]} panelOrder - 当前面板排列顺序
 * @property {Function} toggleFlip - 翻转侧边栏和对话面板位置
 * @property {Function} resetLayout - 重置所有尺寸到默认值
 * @example
 * const { sidebarWidth, chatWidth, toggleFlip } = useLayout()
 */

import { ref, computed } from 'vue'

const DEFAULT_ORDER = ['sidebar', 'center', 'chat']
const FLIPPED_ORDER = ['chat', 'center', 'sidebar']

const sidebarWidth = ref(260)
const chatWidth = ref(360)
const editorRatio = ref(0.55)
const isFlipped = ref(false)

export function useLayout() {
  const panelOrder = computed(() => isFlipped.value ? FLIPPED_ORDER : DEFAULT_ORDER)

  function flipLayout() {
    isFlipped.value = !isFlipped.value
  }

  return {
    sidebarWidth,
    chatWidth,
    editorRatio,
    isFlipped,
    panelOrder,
    flipLayout,
  }
}
