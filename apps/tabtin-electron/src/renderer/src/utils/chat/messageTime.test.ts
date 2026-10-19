/**
 * 任务对话消息时间降级阶梯：刚刚 → N分钟前 → N小时前 → 昨天 → 星期几 → 月日 → 跨年补年份。
 * 重点覆盖 ≥24h 分支（修复前该分支只返回纯时分、不带任何日期）。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { formatTime } from './messageTime'

const tZh = (key: string, options?: Record<string, unknown>): string => {
  switch (key) {
    case 'time.justNow':
      return '刚刚'
    case 'time.minutesAgo':
      return `${options?.count} 分钟前`
    case 'time.hoursAgo':
      return `${options?.count} 小时前`
    case 'time.yesterday':
      return '昨天'
    default:
      return key
  }
}

const tEn = (key: string, _options?: Record<string, unknown>): string => {
  switch (key) {
    case 'time.yesterday':
      return 'Yesterday'
    default:
      return key
  }
}

// 固定“现在”为 2026-10-19（周一）12:00 本地时间
const NOW = new Date(2026, 9, 19, 12, 0, 0)

describe('formatTime 降级阶梯', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(NOW)
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('< 1 分钟 → 刚刚', () => {
    expect(formatTime(new Date(NOW.getTime() - 30_000).toISOString(), tZh, 'zh-CN'))
      .toBe('刚刚')
  })

  it('< 1 小时 → N 分钟前', () => {
    expect(formatTime(new Date(NOW.getTime() - 5 * 60_000).toISOString(), tZh, 'zh-CN'))
      .toBe('5 分钟前')
  })

  it('< 24 小时 → N 小时前', () => {
    expect(formatTime(new Date(NOW.getTime() - 2 * 3_600_000).toISOString(), tZh, 'zh-CN'))
      .toBe('2 小时前')
  })

  it('昨天 → 昨天 + 时分', () => {
    // 2026-10-18（周日）08:15
    expect(formatTime(new Date(2026, 9, 18, 8, 15).toISOString(), tZh, 'zh-CN'))
      .toBe('昨天 08:15')
  })

  it('一周内 → 星期几 + 时分', () => {
    // 2026-10-16（周五）14:30
    expect(formatTime(new Date(2026, 9, 16, 14, 30).toISOString(), tZh, 'zh-CN'))
      .toBe('星期五 14:30')
  })

  it('更早同年 → 月日 + 时分', () => {
    // 2026-09-19 10:05
    expect(formatTime(new Date(2026, 8, 19, 10, 5).toISOString(), tZh, 'zh-CN'))
      .toBe('9月19日 10:05')
  })

  it('跨年 → 年月日 + 时分', () => {
    // 2025-12-30 16:45
    expect(formatTime(new Date(2025, 11, 30, 16, 45).toISOString(), tZh, 'zh-CN'))
      .toBe('2025年12月30日 16:45')
  })

  it('非法时间 → 空串', () => {
    expect(formatTime('not-a-date', tZh, 'zh-CN')).toBe('')
  })

  it('en-US：昨天与星期按语言本地化（en 默认 12 小时制带 AM/PM）', () => {
    expect(formatTime(new Date(2026, 9, 18, 8, 15).toISOString(), tEn, 'en-US'))
      .toBe('Yesterday 08:15 AM')
    expect(formatTime(new Date(2026, 9, 16, 14, 30).toISOString(), tEn, 'en-US'))
      .toBe('Friday 02:30 PM')
    expect(formatTime(new Date(2026, 8, 19, 10, 5).toISOString(), tEn, 'en-US'))
      .toBe('Sep 19 10:05 AM')
  })
})
