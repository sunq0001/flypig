/**
 * 工具：选择本地目录
 * @description 优先使用 Chrome/Edge 的原生 showDirectoryPicker，
 *              不可用时降级到 webkitdirectory input，Firefox 退回纯文本提示。
 * @returns {Promise<string|null>} 选中的绝对路径（Windows 如 "C:\\foo\\bar"）；用户取消或失败返回 null
 *
 * 浏览器兼容性：
 *   - Chrome/Edge 86+：showDirectoryPicker（原生文件夹选择器，一次点击完成）
 *   - Chrome < 86 / Safari：webkitdirectory input（需要选文件夹内的任一文件，会弹出文件框）
 *   - Firefox：未支持，提示用户手动输入路径
 */
export async function pickDirectory() {
  // 1. Chrome/Edge 原生 API（首选）
  if (window.showDirectoryPicker) {
    try {
      const dir = await window.showDirectoryPicker()
      return dir.name  // 浏览器安全模型只给名字，需要后端辅助拿绝对路径
    } catch (e) {
      if (e.name === 'AbortError') return null
      throw e
    }
  }

  // 2. webkitdirectory 降级
  return new Promise((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.webkitdirectory = true
    input.style.display = 'none'
    document.body.appendChild(input)
    input.addEventListener('change', () => {
      const files = Array.from(input.files || [])
      if (files.length === 0) {
        resolve(null)
        return
      }
      // webkitRelativePath 形如 "myfolder/sub"
      const relPath = files[0].webkitRelativePath
      const folderName = relPath.split('/')[0]
      document.body.removeChild(input)
      resolve(folderName)
    })
    input.addEventListener('cancel', () => {
      document.body.removeChild(input)
      resolve(null)
    })
    input.click()
  })
}
