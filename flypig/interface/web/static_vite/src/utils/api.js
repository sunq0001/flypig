/**
 * api.js — 统一 API 层
 *
 * Electron 环境下走 IPC（Node.js fs 模块），Web 环境下降级到 fetch。
 * 组件调用方不需要关心底层实现。
 */

const isElectron = typeof window !== 'undefined' && window.electronAPI

// ── 文件树 ──
export async function readDir(dirPath) {
  if (isElectron) {
    return window.electronAPI.readDir(dirPath)
  }
  const res = await fetch('/api/tree', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: dirPath }),
  })
  if (!res.ok) return []
  const json = await res.json()
  return json.entries || []
}

// ── 文件读取 ──
export async function readFile(filePath) {
  if (isElectron) {
    return window.electronAPI.readFile(filePath)
  }
  const res = await fetch(`/api/file?path=${encodeURIComponent(filePath)}`)
  if (!res.ok) return { type: 'error', message: '读取失败' }
  // 判断是否图片
  const ext = filePath.split('.').pop()?.toLowerCase()
  const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp']
  if (imageExts.includes(ext)) {
    const blob = await res.blob()
    return { type: 'image', data: await blobToBase64(blob), ext }
  }
  const data = await res.json()
  return { type: 'text', content: data.content || '' }
}

// ── 文件写入 ──
export async function writeFile(filePath, content) {
  if (isElectron) {
    return window.electronAPI.writeFile(filePath, content)
  }
  const res = await fetch('/api/file', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: filePath, content }),
  })
  return { ok: res.ok }
}

// ── 配置 ──
export async function getConfig() {
  if (isElectron) {
    return window.electronAPI.getConfig()
  }
  const res = await fetch('/api/config')
  return res.json()
}

export async function setConfig(key, value) {
  if (isElectron) {
    return window.electronAPI.setConfig(key, value)
  }
  await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [key]: value }),
  })
}

function blobToBase64(blob) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result.split(',')[1])
    reader.readAsDataURL(blob)
  })
}
