/**
 * file-extensions.test.js — 文件扩展名配置测试
 *
 * 纯数据测试，不依赖 Vue / DOM
 */
import { describe, it, expect } from 'vitest'
import { CODE_EXTENSIONS, DOC_EXTENSIONS, IMAGE_EXTENSIONS } from '@/config/file-extensions.js'

describe('file-extensions config', () => {
  it('code extensions should contain common languages', () => {
    expect(CODE_EXTENSIONS).toContain('js')
    expect(CODE_EXTENSIONS).toContain('py')
    expect(CODE_EXTENSIONS).toContain('vue')
    expect(CODE_EXTENSIONS).toContain('ts')
    expect(CODE_EXTENSIONS).toContain('rs')
  })

  it('doc extensions should contain office formats', () => {
    expect(DOC_EXTENSIONS).toContain('pdf')
    expect(DOC_EXTENSIONS).toContain('docx')
    expect(DOC_EXTENSIONS).toContain('xlsx')
    expect(DOC_EXTENSIONS).toContain('pptx')
  })

  it('image extensions should contain common image formats', () => {
    expect(IMAGE_EXTENSIONS).toContain('png')
    expect(IMAGE_EXTENSIONS).toContain('jpg')
    expect(IMAGE_EXTENSIONS).toContain('svg')
    expect(IMAGE_EXTENSIONS).toContain('gif')
  })

  it('extensions should be unique', () => {
    const all = [...CODE_EXTENSIONS, ...DOC_EXTENSIONS, ...IMAGE_EXTENSIONS]
    const unique = new Set(all)
    expect(unique.size).toBe(all.length)
  })
})
