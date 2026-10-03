/**
 * editor-languages.js — 文件扩展名 → Monaco Editor language ID 映射
 *
 * 数据与代码分离：映射表属于配置数据，统一放在 config/ 下维护，
 * 编辑器组件只通过 getLanguage() 查询，不内嵌映射表。
 */
const langMap = {
  js: 'javascript', ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
  vue: 'html', py: 'python', json: 'json', md: 'markdown',
  html: 'html', css: 'css', scss: 'scss', less: 'less',
  yml: 'yaml', yaml: 'yaml', toml: 'ini',
  xml: 'xml', svg: 'xml', sh: 'shell', bash: 'shell',
  sql: 'sql', go: 'go', rust: 'rust', java: 'java',
  kt: 'kotlin', swift: 'swift', rb: 'ruby', php: 'php',
  pl: 'perl', lua: 'lua', r: 'r', dart: 'dart',
  tex: 'latex', graphql: 'graphql', dockerfile: 'dockerfile',
}

export function getLanguage(ext) {
  return langMap[ext] || 'plaintext'
}
