/**
 * file-icons.js — 文件扩展名 → vscode-icons 图标名映射
 *
 * 数据与代码分离：图标映射表属于配置数据，统一放在 config/ 下维护，
 * 文件树组件只通过 getFileIcon() 查询，不内嵌映射表。
 */
const iconMap = {
  js: 'vscode-icons:file-type-js', ts: 'vscode-icons:file-type-typescript',
  vue: 'vscode-icons:file-type-vue', py: 'vscode-icons:file-type-python',
  json: 'vscode-icons:file-type-json', md: 'vscode-icons:file-type-markdown',
  html: 'vscode-icons:file-type-html', css: 'vscode-icons:file-type-css',
  yml: 'vscode-icons:file-type-yaml', yaml: 'vscode-icons:file-type-yaml',
  toml: 'vscode-icons:file-type-toml',
  png: 'vscode-icons:file-type-image', jpg: 'vscode-icons:file-type-image',
  jpeg: 'vscode-icons:file-type-image', svg: 'vscode-icons:file-type-image',
  txt: 'vscode-icons:file-type-text',
  gitignore: 'vscode-icons:file-type-git',
}

export function getFileIcon(ext) {
  return iconMap[ext] || 'vscode-icons:default-file'
}
