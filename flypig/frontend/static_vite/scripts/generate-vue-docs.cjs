/**
 * generate-vue-docs.cjs
 * 用 vue-docgen-api 扫描 .vue 组件 + .js composables/lib/stores，
 * 自动生成 API 文档 markdown
 *
 * 用法: node scripts/generate-vue-docs.cjs
 * 输出: docs/api-docs-vue/ 下每个源文件一个 .md 文件
 */
const path = require('path')
const fs = require('fs')
const { parse } = require('vue-docgen-api')

const ROOT = path.resolve(__dirname, '..')                        // flypig/frontend/static_vite
const WORKSPACE = path.resolve(ROOT, '../../..')                   // workspace root
const SRC_DIR = path.join(ROOT, 'src')
const OUT_DIR = path.join(WORKSPACE, 'docs/api-docs-vue/src')

// 扫描文件（.vue + .js 都扫描）
function findSourceFiles(dir) {
  const files = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory() && !entry.name.startsWith('.')) {
      files.push(...findSourceFiles(full))
    } else if (entry.isFile() && (entry.name.endsWith('.vue') || entry.name.endsWith('.js'))) {
      files.push(full)
    }
  }
  return files
}

// 提取 HTML 文件头注释（用于 .vue 文件）
function extractHtmlComment(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8')
  const match = raw.match(/<!--\s*([\s\S]*?)-->/)
  if (match) {
    return match[1].split('\n').map(l => l.trim()).filter(Boolean)
  }
  return []
}

// 解析 JSDoc 注释块 → { description, params, returns, properties, examples }
function parseJSDoc(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8')
  const jsdocMatch = raw.match(/\/\*\*([\s\S]*?)\*\//)
  if (!jsdocMatch) return null

  const block = jsdocMatch[1]
  const lines = block.split('\n').map(l => l.replace(/^\s*\* ?/, '').trim())

  const result = { description: '', descriptionExtra: [], params: [], returns: null, properties: [], examples: [] }
  let currentSection = 'description'

  for (const line of lines) {
    if (line.startsWith('@module ')) {
      result.module = line.replace('@module ', '').trim()
    } else if (line.startsWith('@description ')) {
      result.description = line.replace('@description ', '').trim()
      currentSection = 'description'
    } else if (line.startsWith('@param ')) {
      const p = parseParamTag(line)
      if (p) result.params.push(p)
      currentSection = 'param'
    } else if (line.startsWith('@returns ') || line.startsWith('@return ')) {
      const r = parseReturnsTag(line)
      if (r) result.returns = r
    } else if (line.startsWith('@property ')) {
      const p = parseParamTag(line.replace('@property', '@param'))
      if (p) result.properties.push(p)
    } else if (line.startsWith('@example')) {
      currentSection = 'example'
      const inlineText = line.replace('@example', '').trim()
      result.examples.push({ text: inlineText, code: '' })
    } else if (line.startsWith('@')) {
      currentSection = 'other'
    } else if (line) {
      // 非空、非标签行
      if (currentSection === 'description') {
        if (!result.description) {
          result.description = line
        } else {
          result.descriptionExtra.push(line)
        }
      } else if (currentSection === 'example' && result.examples.length > 0) {
        const last = result.examples[result.examples.length - 1]
        if (last && !last.code) last.code = ''
        if (last) last.code += (last.code ? '\n' : '') + line
      }
    }
  }

  return result
}

function parseParamTag(line) {
  // @param {type} name - description
  const match = line.match(/@param\s+(?:\{([^}]+)\})?\s*(\w+)\s*-?\s*(.*)/)
  if (!match) return null
  return { name: match[2], type: match[1] || '', description: match[3].trim() }
}

function parseReturnsTag(line) {
  // @returns {type} description
  const match = line.match(/@returns?\s+(?:\{([^}]+)\})?\s*(.*)/)
  if (!match) return null
  return { type: match[1] || '', description: match[2].trim() }
}

// 从 JSDoc 结果渲染 markdown
function renderJSDoc(result) {
  if (!result) return ''
  let md = ''
  if (result.description) md += `> ${result.description}\n\n`

  // 额外描述行（为什么做/实现方法/实现效果）
  for (const line of result.descriptionExtra) {
    if (line.startsWith('为什么做：')) {
      md += `> **需求**：${line.replace('为什么做：', '')}\n>\n`
    } else if (line.startsWith('实现方法：')) {
      md += `> **方案**：${line.replace('实现方法：', '')}\n>\n`
    } else if (line.startsWith('实现效果：')) {
      md += `> **效果**：${line.replace('实现效果：', '')}\n>\n`
    } else if (line.startsWith('技术栈：')) {
      md += `> **技术栈**：${line.replace('技术栈：', '')}\n>\n`
    } else if (line.startsWith('层&依赖：')) {
      md += `> **层&依赖**：${line.replace('层&依赖：', '')}\n>\n`
    } else if (line.startsWith('细节见文档：')) {
      md += `> **参考文档**：${line.replace('细节见文档：', '')}\n>\n`
    }
  }
  if (result.descriptionExtra.length > 0) md += '\n'

  if (result.returns) {
    md += `**返回值**：\`${result.returns.type}\` — ${result.returns.description}\n\n`
  }

  if (result.params.length > 0) {
    md += `### 参数\n\n`
    const rows = result.params.map(p => ({
      名称: p.name, 类型: p.type, 描述: p.description
    }))
    md += renderTable(rows, ['名称', '类型', '描述'])
    md += '\n\n'
  }

  if (result.properties.length > 0) {
    md += `### 属性\n\n`
    const rows = result.properties.map(p => ({
      名称: p.name, 类型: p.type, 描述: p.description
    }))
    md += renderTable(rows, ['名称', '类型', '描述'])
    md += '\n\n'
  }

  if (result.examples.length > 0) {
    md += `### 示例\n\n`
    for (const ex of result.examples) {
      if (ex.text) md += `${ex.text}\n`
      if (ex.code) md += `\`\`\`javascript\n${ex.code.trim()}\n\`\`\`\n\n`
    }
  }

  return md
}

// 渲染 Vue 文件头注释
function renderVueComment(lines) {
  if (!lines || lines.length === 0) return ''
  const title = lines[0]
  let md = `> **${title}**\n>\n`
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]
    if (line.startsWith('为什么做：')) {
      md += `> **需求**：${line.replace('为什么做：', '')}\n>\n`
    } else if (line.startsWith('实现方法：')) {
      md += `> **方案**：${line.replace('实现方法：', '')}\n>\n`
    } else if (line.startsWith('实现效果：')) {
      md += `> **效果**：${line.replace('实现效果：', '')}\n>\n`
    } else if (line.startsWith('技术栈：')) {
      md += `> **技术栈**：${line.replace('技术栈：', '')}\n>\n`
    } else if (line.startsWith('层&依赖：')) {
      md += `> **层&依赖**：${line.replace('层&依赖：', '')}\n>\n`
    } else if (line.startsWith('细节见文档：')) {
      md += `> **参考文档**：${line.replace('细节见文档：', '')}\n>\n`
    }
  }
  return md.trimEnd() + '\n\n'
}

function renderTable(rows, headers) {
  if (!rows || rows.length === 0) return ''
  const headerLine = `| ${headers.join(' | ')} |`
  const separator = `| ${headers.map(() => '---').join(' | ')} |`
  const bodyLines = rows.map(row => {
    const cells = headers.map(h => {
      let val = row[h] !== undefined ? String(row[h]) : ''
      val = val.replace(/\n/g, '<br>')
      val = val.replace(/\|/g, '\\|')
      return val
    })
    return `| ${cells.join(' | ')} |`
  })
  return [headerLine, separator, ...bodyLines].join('\n')
}

// 处理单个文件，返回 { relPath, mdContent }
async function processFile(filePath) {
  const relPath = path.relative(SRC_DIR, filePath).replace(/\\/g, '/')
  const isVue = filePath.endsWith('.vue')

  // .js 文件：直接用 JSDoc 解析器，跳过 vue-docgen-api
  if (!isVue) {
    const jsdoc = parseJSDoc(filePath)
    let md = `# ${relPath}\n\n`
    md += renderJSDoc(jsdoc)
    if (!jsdoc) md += '_该文件无 JSDoc 注释。_\n'
    return { relPath, md }
  }

  // .vue 文件：用 vue-docgen-api 解析
  try {
    const docs = await parse(filePath, { jsx: true })

    if (!docs || Object.keys(docs).length === 0) {
      let md = `# ${relPath}\n\n`
      md += renderVueComment(extractHtmlComment(filePath))
      md += '_该组件无 props/events/slots/methods 可供自动提取。_\n'
      return { relPath, md }
    }

    let md = `# ${relPath}\n\n`
    md += renderVueComment(extractHtmlComment(filePath))
    if (docs.description) md += `${docs.description}\n\n`

    // 标签
    if (docs.tags && docs.tags.length > 0) {
      const showTags = docs.tags.filter(t => !['module', 'description'].includes(t.title))
      if (showTags.length > 0) {
        md += `## 标签\n\n`
        for (const tag of showTags) {
          md += `- **@${tag.title}**${tag.description ? ': ' + tag.description : ''}\n`
        }
        md += '\n'
      }
    }

    // Props
    if (docs.props && docs.props.length > 0) {
      md += `## Props\n\n`
      const rows = docs.props.map(p => ({
        名称: p.name, 类型: p.type ? p.type.name : '-',
        默认值: p.defaultValue ? String(p.defaultValue.value) : '-',
        必填: p.required ? '是' : '否', 描述: p.description || ''
      }))
      md += renderTable(rows, ['名称', '类型', '默认值', '必填', '描述'])
      md += '\n\n'
    }

    // Events
    if (docs.events && docs.events.length > 0) {
      md += `## Events\n\n`
      const rows = docs.events.map(e => ({ 名称: e.name, 描述: e.description || '-' }))
      md += renderTable(rows, ['名称', '描述'])
      md += '\n\n'
    }

    // Slots
    if (docs.slots && docs.slots.length > 0) {
      md += `## Slots\n\n`
      const rows = docs.slots.map(s => ({ 名称: s.name, 描述: s.description || '-' }))
      md += renderTable(rows, ['名称', '描述'])
      md += '\n\n'
    }

    // Methods
    if (docs.methods && docs.methods.length > 0) {
      md += `## Methods\n\n`
      const rows = docs.methods.map(m => ({ 名称: m.name, 描述: m.description || '-' }))
      md += renderTable(rows, ['名称', '描述'])
      md += '\n\n'
    }

    return { relPath, md }
  } catch (e) {
    let md = `# ${relPath}\n\n`
    md += renderVueComment(extractHtmlComment(filePath))
    md += `_API 解析失败: ${e.message}_\n`
    return { relPath, md }
  }
}

// 按子目录分组文件，生成索引页
function generateIndex(files, dir, label) {
  const groups = {}
  for (const fp of files) {
    const rel = path.relative(dir, fp).replace(/\\/g, '/')
    const d = path.dirname(rel)
    if (!groups[d]) groups[d] = []
    groups[d].push({ path: rel, name: path.basename(fp, path.extname(fp)) })
  }

  let md = ''
  for (const [d, items] of Object.entries(groups)) {
    const l = d === '.' ? '根目录' : d
    md += `### ${l}\n\n`
    for (const f of items) {
      const docPath = f.path.replace(/\.\w+$/i, '').replace(/\\/g, '/')
      md += `- [${f.name}](./src/${docPath}.md)\n`
    }
    md += '\n'
  }
  return md
}

async function generateDocs() {
  const allFiles = findSourceFiles(SRC_DIR)
  const vueFiles = allFiles.filter(f => f.endsWith('.vue'))
  const jsFiles = allFiles.filter(f => f.endsWith('.js'))
  console.log(`找到 ${vueFiles.length} 个 .vue + ${jsFiles.length} 个 .js 文件`)

  // 清空输出
  if (fs.existsSync(OUT_DIR)) fs.rmSync(OUT_DIR, { recursive: true })

  let parsed = 0
  for (const filePath of allFiles) {
    const { relPath, md } = await processFile(filePath)
    const outName = relPath.replace(/\.\w+$/i, '.md')
    const outPath = path.join(OUT_DIR, outName)
    fs.mkdirSync(path.dirname(outPath), { recursive: true })
    fs.writeFileSync(outPath, md, 'utf-8')
    parsed++
    console.log(`  ${filePath.endsWith('.vue') ? '✓' : '📦'} ${relPath}`)
  }

  // 生成索引
  const vueIndex = generateIndex(vueFiles, SRC_DIR, 'Vue 组件')
  const jsIndex = generateIndex(jsFiles, SRC_DIR, 'JS 模块')

  let indexMd = `# FlyPig 前端文档\n\n`
  indexMd += `自动从 \`src/\` 目录生成。共 ${allFiles.length} 个源文件（${vueFiles.length} 个组件 + ${jsFiles.length} 个 JS 模块）。\n\n`
  indexMd += `---\n\n## Vue 组件\n\n${vueIndex}\n---\n\n## JS 模块（composables / lib / stores）\n\n${jsIndex}\n`

  fs.writeFileSync(path.join(WORKSPACE, 'docs/api-docs-vue/index.md'), indexMd, 'utf-8')
  console.log(`\n完成: ${parsed} 个文件, 索引页: docs/api-docs-vue/index.md`)
}

generateDocs().catch(e => {
  console.error('生成失败:', e.message)
  process.exit(1)
})
