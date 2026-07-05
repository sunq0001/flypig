/**
 * getFileUrl.test.js — api.js 纯函数测试
 *
 * getFileUrl 不依赖 fetch/window，是纯函数
 */
import { describe, it, expect } from 'vitest'
import { getFileUrl } from '@/utils/api.js'

describe('getFileUrl', () => {
  it('should encode path properly', () => {
    const url = getFileUrl('/path/to/file.txt')
    expect(url).toBe('/api/file?path=%2Fpath%2Fto%2Ffile.txt')
  })

  it('should handle paths with spaces', () => {
    const url = getFileUrl('/path/with space.txt')
    expect(url).toContain(encodeURIComponent('/path/with space.txt'))
  })

  it('should handle paths with Chinese characters', () => {
    const url = getFileUrl('/中文/file.txt')
    expect(url).toContain(encodeURIComponent('/中文/file.txt'))
  })
})
