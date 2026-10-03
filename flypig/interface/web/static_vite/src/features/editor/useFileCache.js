/**
 * useFileCache — 文件系统缓存
 *
 * 启动时一次性递归加载整个工作区的目录树和文件内容，
 * 之后所有展开/查看操作都在前端缓存中完成，不依赖后端。
 */
import { ref, shallowRef } from 'vue'

// 单例缓存（所有组件共享）
const treeCache = shallowRef({})     // path → { name, type, children[] }
const contentCache = shallowRef({})  // path → string
const loading = ref(false)

async function fetchDir(path) {
  try {
    const res = await fetch('/api/tree', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    })
    if (!res.ok) return []
    const json = await res.json()
    return (json.entries || []).map(e => ({ ...e, children: null }))
  } catch { return [] }
}

async function loadDirRecursive(path) {
  try {
    const entries = await fetchDir(path)
    treeCache.value[path] = { entries, loaded: true }
    for (const e of entries) {
      if (e.type === 'directory') {
        await loadDirRecursive(e.path)
      }
    }
    return entries
  } catch { return [] }
}

export function useFileCache() {
  async function preload(rootPath) {
    if (!rootPath || treeCache.value[rootPath]?.loaded) return
    loading.value = true
    try {
      await loadDirRecursive(rootPath)
    } catch {
      // 预加载失败不影响后续操作
    } finally {
      loading.value = false
    }
  }

  function getChildren(path) {
    return treeCache.value[path]?.entries || []
  }

  async function getFileContent(path) {
    if (contentCache.value[path]) return contentCache.value[path]
    try {
      const res = await fetch(`/api/file?path=${encodeURIComponent(path)}`)
      if (!res.ok) return '无法读取文件'
      const data = await res.json()
      contentCache.value[path] = data.content || ''
      return contentCache.value[path]
    } catch { return '读取失败' }
  }

  function isLoaded(path) {
    return !!treeCache.value[path]?.loaded
  }

  return { preload, getChildren, getFileContent, isLoaded, loading }
}
