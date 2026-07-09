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
  try {
    const res = await fetch('/api/tree', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: dirPath }),
    })
    if (!res.ok) return []
    const json = await res.json()
    return json.entries || []
  } catch {
    return []
  }
}

// ── 文件读取 ──
export async function readFile(filePath) {
  if (isElectron) {
    return window.electronAPI.readFile(filePath)
  }
  try {
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
  } catch {
    return { type: 'error', message: '读取失败' }
  }
}

// ── 文件 URL（用于 <img src> 等场景）──
export function getFileUrl(path) {
  return `/api/file?path=${encodeURIComponent(path)}`
}

// ── 文件写入 ──
export async function writeFile(filePath, content) {
  if (isElectron) {
    return window.electronAPI.writeFile(filePath, content)
  }
  try {
    const res = await fetch('/api/file', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: filePath, content }),
    })
    return { ok: res.ok }
  } catch {
    return { ok: false }
  }
}

// ── 配置 ──
export async function getConfig() {
  if (isElectron) {
    return window.electronAPI.getConfig()
  }
  try {
    const res = await fetch('/api/config')
    return res.json()
  } catch {
    return {}
  }
}

export async function setConfig(key, value) {
  if (isElectron) {
    return window.electronAPI.setConfig(key, value)
  }
  try {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: value }),
    })
  } catch {
    // 静默
  }
}

// ── 配置（扩展） ──
export async function updateDefaultModel(modelName) {
  try {
    await fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ default_model: modelName }),
    })
  } catch {
    // 静默
  }
}

export async function saveApiKey(provider, apiKey) {
  try {
    const res = await fetch('/api/config/apikey', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key: apiKey }),
    })
    return { ok: res.ok }
  } catch {
    return { ok: false }
  }
}

// ── 文件浏览 ──
export async function browseDir(parentPath) {
  try {
    const res = await fetch('/api/config/browse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: parentPath }),
    })
    if (!res.ok) return { entries: [], parent: '', path: '' }
    return res.json()
  } catch {
    return { entries: [], parent: '', path: '' }
  }
}

export async function mkdirDir(parentPath, name) {
  try {
    const res = await fetch('/api/config/mkdir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parent: parentPath, name }),
    })
    return { ok: res.ok }
  } catch {
    return { ok: false }
  }
}

// ── 本地模型 ──
export async function getLocalModels() {
  try {
    const res = await fetch('/api/config/local-models')
    if (!res.ok) return { running: false, installed: [] }
    return res.json()
  } catch {
    return { running: false, installed: [] }
  }
}

// ── 定价 ──
export async function getPricing(currency) {
  try {
    const res = await fetch(`/api/pricing?currency=${currency}`)
    if (!res.ok) return { prices: {} }
    return res.json()
  } catch {
    return { prices: {} }
  }
}

function blobToBase64(blob) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result.split(',')[1])
    reader.readAsDataURL(blob)
  })
}
