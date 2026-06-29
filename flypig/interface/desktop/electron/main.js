// flypig/interface/desktop/electron/main.js — Electron 主进程
// 替代 Python 后端：文件操作、配置管理直接在 Node.js 中完成

const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const fs = require('fs')

const ROOT = path.resolve(__dirname, '..', '..', '..', '..') // 项目根
const isDev = !app.isPackaged

let mainWindow = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 600,
    title: 'FlyPig Agent',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    mainWindow.loadFile(path.join(ROOT, 'flypig', 'interface', 'web', 'static_vite', 'dist', 'index.html'))
  }
}

// ── IPC: 文件树 ──
ipcMain.handle('fs:readDir', async (_, dirPath) => {
  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true })
    return entries
      .filter(e => !e.name.startsWith('.'))
      .sort((a, b) => {
        if (a.isDirectory() && !b.isDirectory()) return -1
        if (!a.isDirectory() && b.isDirectory()) return 1
        return a.name.localeCompare(b.name)
      })
      .map(e => ({
        name: e.name,
        path: path.join(dirPath, e.name),
        type: e.isDirectory() ? 'directory' : 'file',
      }))
  } catch {
    return []
  }
})

// ── IPC: 文件读写 ──
ipcMain.handle('fs:readFile', async (_, filePath) => {
  try {
    const ext = path.extname(filePath).toLowerCase()
    const imageExts = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp']
    if (imageExts.includes(ext)) {
      const data = fs.readFileSync(filePath)
      return { type: 'image', data: data.toString('base64'), ext }
    }
    return { type: 'text', content: fs.readFileSync(filePath, 'utf-8') }
  } catch (e) {
    return { type: 'error', message: e.message }
  }
})

ipcMain.handle('fs:writeFile', async (_, filePath, content) => {
  try {
    fs.writeFileSync(filePath, content, 'utf-8')
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e.message }
  }
})

// ── IPC: 配置读写 ──
const CONFIG_PATH = path.join(ROOT, 'config.yaml')

ipcMain.handle('config:get', async () => {
  try {
    if (!fs.existsSync(CONFIG_PATH)) return {}
    const yaml = require('js-yaml')
    return yaml.load(fs.readFileSync(CONFIG_PATH, 'utf-8')) || {}
  } catch {
    return {}
  }
})

ipcMain.handle('config:set', async (_, key, value) => {
  try {
    const yaml = require('js-yaml')
    let config = {}
    if (fs.existsSync(CONFIG_PATH)) {
      config = yaml.load(fs.readFileSync(CONFIG_PATH, 'utf-8')) || {}
    }
    config[key] = value
    fs.writeFileSync(CONFIG_PATH, yaml.dump(config), 'utf-8')
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e.message }
  }
})

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
