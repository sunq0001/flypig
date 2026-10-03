/**
 * 文件变更事件集中管理 Store
 *
 * 职责：
 * - 维护一个响应式计数器 `fileChangeVersion`，每次文件发生变更时 +1
 * - 后端 SSE (file-events + tool-events) 推送到此 Store
 * - 所有组件（FileTree、EditorPane 等）通过 watch 订阅变化
 *
 * 大厂模式：Pinia 或 composable，统一事件源，组件间不直接通讯
 */
import { ref } from 'vue'

/** 文件变更计数器，任何文件变化时 +1 */
const fileChangeVersion = ref(0)

/** SSE 连接实例 */
let fileEventSource = null

/** 手动触发刷新（AI 流结束时调用） */
export function triggerFileChange() {
  fileChangeVersion.value++
}

/**
 * 建立 SSE 连接，持续监听后端文件变更
 * 在 App.vue 或 layout 级组件启动一次即可
 */
export function connectFileEvents() {
  if (!fileEventSource) {
    fileEventSource = new EventSource('/api/events/files')
    fileEventSource.onmessage = () => {
      fileChangeVersion.value++
    }
    fileEventSource.onerror = () => {}
  }
}

/** 断开 SSE 连接（页面卸载时） */
export function disconnectFileEvents() {
  if (fileEventSource) { fileEventSource.close(); fileEventSource = null }
}

/**
 * 组件组合式 API 入口
 * 使用：const { version } = useFileEvents()
 */
export function useFileEvents() {
  return { fileChangeVersion }
}
