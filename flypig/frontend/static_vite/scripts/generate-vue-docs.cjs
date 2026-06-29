/**
 * generate-vue-docs.cjs
 * 用 vue-docgen-api 扫描 .vue 组件，自动生成 API 文档 markdown
 *
 * 用法: node scripts/generate-vue-docs.cjs
 * 输出: docs/api-docs-vue/components/ 下每个组件一个 .md 文件
 */
const path = require('path')
const fs = require('fs')
const { parse } = require('vue-docgen-api')

const ROOT = path.resolve(__dirname, '..')                          // flypig/frontend/static_vite
const WORKSPACE = path.resolve(ROOT, '../../..')                     // 工作区根目录
const SRC_DIR = path.join(ROOT, 'src')
const OUT_DIR = path.join(WORKSPACE, 'docs/api-docs-vue/components')

// 扫描所有 .vue 文件
function findVueFiles(dir) {
  const files = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory() && !entry.name.startsWith('.')) {
      files.push(...findVueFiles(full))
    } else if (entry.isFile() && entry.name.endsWith('.vue')) {
      files.push(full)
    }
  }
  return files
}

// 清理 HTML 注释
function stripHtmlComments(text) {
  return text.replace(/<!--[\s\S]*?-->/g, '').trim()
}

// 从文件头注释提取完整描述（含多段信息）
function extractDescription(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8')
  const match = raw.match(/<!--\s*([\s\S]*?)-->/)
  if (match) {
    const lines = match[1].split('\n').map(l => l.trim()).filter(Boolean)
    return lines  // 返回所有非空行数组
  }
  return []
}

// 从文件头注释提取结构化文档
function renderHeaderComment(lines) {
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
      // 处理多行，如 @description
      val = val.replace(/\n/g, '<br>')
      // 转义 |
      val = val.replace(/\|/g, '\\|')
      return val
    })
    return `| ${cells.join(' | ')} |`
  })
  return [headerLine, separator, ...bodyLines].join('\n')
}

async function generateDocs() {
  const vueFiles = findVueFiles(SRC_DIR)
  console.log(`找到 ${vueFiles.length} 个 .vue 文件`)

  // 清空输出目录
  if (fs.existsSync(OUT_DIR)) {
    fs.rmSync(OUT_DIR, { recursive: true })
  }
  fs.mkdirSync(OUT_DIR, { recursive: true })

  let parsed = 0
  let failed = 0

  for (const filePath of vueFiles) {
    const relPath = path.relative(SRC_DIR, filePath).replace(/\\/g, '/')
    const outName = relPath.replace(/\.vue$/i, '.md')
    const outPath = path.join(OUT_DIR, outName)

    // 保持子目录结构
    fs.mkdirSync(path.dirname(outPath), { recursive: true })

    try {
      const docs = await parse(filePath, { jsx: true })

      if (!docs || Object.keys(docs).length === 0) {
        // 组件没有可提取的 API（无 defineProps/defineEmits/defineExpose）
        const descLines = extractDescription(filePath)
        const desc = renderHeaderComment(descLines)
        const content = `# ${relPath}\n\n${desc}_该组件无 props/events/slots/methods 可供自动提取。_\n`
        fs.writeFileSync(outPath, content, 'utf-8')
        continue
      }

      parsed++
      let md = `# ${relPath}\n\n`

      // 组件描述（从文件头注释 + vue-docgen-api）
      const descLines = extractDescription(filePath)
      md += renderHeaderComment(descLines)
      if (docs.description) md += `${docs.description}\n\n`

      // 标签
      if (docs.tags && docs.tags.length > 0) {
        md += `## 标签\n\n`
        for (const tag of docs.tags) {
          md += `- **@${tag.title}**${tag.description ? ': ' + tag.description : ''}\n`
        }
        md += '\n'
      }

      // Props
      if (docs.props && docs.props.length > 0) {
        md += `## Props\n\n`
        const rows = docs.props.map(p => ({
          名称: p.name,
          类型: p.type ? p.type.name : '-',
          默认值: p.defaultValue ? String(p.defaultValue.value) : '-',
          必填: p.required ? '是' : '否',
          描述: p.description || ''
        }))
        md += renderTable(rows, ['名称', '类型', '默认值', '必填', '描述'])
        md += '\n\n'
      }

      // Events
      if (docs.events && docs.events.length > 0) {
        md += `## Events\n\n`
        const rows = docs.events.map(e => ({
          名称: e.name,
          描述: e.description || '-'
        }))
        md += renderTable(rows, ['名称', '描述'])
        md += '\n\n'
      }

      // Slots
      if (docs.slots && docs.slots.length > 0) {
        md += `## Slots\n\n`
        const rows = docs.slots.map(s => ({
          名称: s.name,
          描述: s.description || '-'
        }))
        md += renderTable(rows, ['名称', '描述'])
        md += '\n\n'
      }

      // Methods
      if (docs.methods && docs.methods.length > 0) {
        md += `## Methods\n\n`
        const rows = docs.methods.map(m => ({
          名称: m.name,
          描述: m.description || '-'
        }))
        md += renderTable(rows, ['名称', '描述'])
        md += '\n\n'
      }

      fs.writeFileSync(outPath, md, 'utf-8')
      console.log(`  ✓ ${relPath}`)
    } catch (e) {
      failed++
      const descLines = extractDescription(filePath)
      const desc = renderHeaderComment(descLines)
      const content = `# ${relPath}\n\n${desc}_API 解析失败: ${e.message}_\n`
      fs.writeFileSync(outPath, content, 'utf-8')
      console.log(`  ✗ ${relPath} (${e.message})`)
    }
  }

  // 生成索引页
  const indexMd = generateIndexPage(vueFiles)
  fs.writeFileSync(path.join(path.dirname(OUT_DIR), 'components.md'), indexMd, 'utf-8')

  console.log(`\n完成: ${parsed} 个解析成功, ${failed} 个解析失败, 共 ${vueFiles.length} 个组件`)
}

function generateIndexPage(vueFiles) {
  let md = `# Vue 组件文档\n\n自动从 \`frontend/static_vite/src/\` 目录下的 \`.vue\` 文件生成。\n\n`
  md += `共 ${vueFiles.length} 个组件。\n\n`

  // 按子目录分组
  const groups = {}
  const SRC_DIR = path.resolve(__dirname, '..', 'src')
  for (const fp of vueFiles) {
    const rel = path.relative(SRC_DIR, fp).replace(/\\/g, '/')
    const dir = path.dirname(rel)
    if (!groups[dir]) groups[dir] = []
    groups[dir].push({ path: rel, name: path.basename(fp, '.vue') })
  }

  for (const [dir, files] of Object.entries(groups)) {
    const label = dir === '.' ? '根目录' : dir
    md += `### ${label}\n\n`
    for (const f of files) {
      const docPath = f.path.replace(/\.vue$/i, '').replace(/\\/g, '/')
      md += `- [${f.name}](./components/${docPath}.md)\n`
    }
    md += '\n'
  }
  return md
}

generateDocs().catch(e => {
  console.error('生成失败:', e.message)
  process.exit(1)
})
