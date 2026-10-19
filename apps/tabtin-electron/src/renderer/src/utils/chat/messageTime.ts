type Translate = (key: string, options?: Record<string, unknown>) => string

const RETIRED_INTENT_LABELS_ZH: Record<string, string> = {
  ask_user_required: '需要回答',
  review_required: '需要审批',
}

const RETIRED_INTENT_LABELS_EN: Record<string, string> = {
  ask_user_required: 'Answer Required',
  review_required: 'Approval Required',
}

const ONE_MINUTE_MS = 60_000
const ONE_HOUR_MS = 60 * ONE_MINUTE_MS
const ONE_DAY_MS = 24 * ONE_HOUR_MS
const ONE_WEEK_MS = 7 * ONE_DAY_MS

export function formatTime(
  dateString: string,
  t: Translate,
  locale: string,
): string {
  try {
    const date = new Date(dateString)
    if (Number.isNaN(date.getTime())) return ''
    const now = new Date()
    const diff = now.getTime() - date.getTime()

    if (diff < ONE_MINUTE_MS) {
      return t('time.justNow')
    }

    if (diff < ONE_HOUR_MS) {
      return t('time.minutesAgo', { count: Math.floor(diff / ONE_MINUTE_MS) })
    }

    if (diff < ONE_DAY_MS) {
      return t('time.hoursAgo', { count: Math.floor(diff / ONE_HOUR_MS) })
    }

    // 24 小时以前：对齐 IM（dateUtils）与中国用户习惯的降级阶梯——
    // 昨天 → 一周内星期几 → 月日 → 跨年补年份，时分始终在场，
    // 修复此前「历史消息只剩纯时分、无任何日期」的问题。
    const effectiveLocale = locale || 'en-US'
    const clock = date.toLocaleTimeString(effectiveLocale, {
      hour: '2-digit',
      minute: '2-digit',
    })

    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)
    if (date.toDateString() === yesterday.toDateString()) {
      return `${t('time.yesterday')} ${clock}`
    }

    if (diff < ONE_WEEK_MS) {
      // 前天～一周内：星期五 14:30（星期名由 Intl 按语言本地化）
      const weekday = date.toLocaleDateString(effectiveLocale, { weekday: 'long' })
      return `${weekday} ${clock}`
    }

    const sameYear = date.getFullYear() === now.getFullYear()
    const datePart = date.toLocaleDateString(
      effectiveLocale,
      sameYear
        ? { month: 'short', day: 'numeric' }
        : { year: 'numeric', month: 'short', day: 'numeric' },
    )
    return `${datePart} ${clock}`
  } catch {
    return ''
  }
}

export function getIntentLabel(
  intent: string,
  t: Translate,
  language?: string,
): string {
  const key = `intent.${intent}`
  const label = t(key, { defaultValue: '' })
  if (label) return label
  const lang = (language || 'en').toLowerCase()
  const fallback = lang.startsWith('zh')
    ? RETIRED_INTENT_LABELS_ZH[intent]
    : RETIRED_INTENT_LABELS_EN[intent]
  return fallback || intent
}
