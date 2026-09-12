/**
 * AskPage — 问一句页面（轻量即时问答入口）。
 *
 * 纯输入框 + 大家常问 + 最近问答。不建任务、不助手承办、无交付物。
 * 比办件事简单更多——不依赖任何任务域 store / 空间上下文。
 */

import React, { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageSquare, Search } from 'lucide-react'

interface RecentQA {
  id: string
  question: string
  answer: string
  timestamp: number
}

const SUGGESTED_QUESTIONS = [
  '如何创建工作空间？',
  '怎么导入外部数据？',
  '技能和连接器有什么区别？',
  '如何分享文档给团队成员？',
]

// 本地 localStorage 持久化最近问答
const STORAGE_KEY = 'ask-page-recent-qa'
const MAX_RECENT = 20

function loadRecentQA(): RecentQA[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw) as RecentQA[]
  } catch {
    return []
  }
}

function saveRecentQA(list: RecentQA[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, MAX_RECENT)))
  } catch {
    // ignore
  }
}

export const AskPage: React.FC = () => {
  const { t } = useTranslation(['sidebar'])
  const [input, setInput] = useState('')
  const [recentQA, setRecentQA] = useState<RecentQA[]>(() => loadRecentQA())

  const handleAsk = useCallback(() => {
    const question = input.trim()
    if (!question) return
    const qa: RecentQA = {
      id: `${Date.now()}`,
      question,
      answer: '',
      timestamp: Date.now(),
    }
    const next = [qa, ...recentQA].slice(0, MAX_RECENT)
    setRecentQA(next)
    saveRecentQA(next)
    setInput('')
  }, [input, recentQA])

  const handleSuggestionClick = useCallback((q: string) => {
    setInput(q)
  }, [])

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      {/* 输入区 */}
      <div className="px-8 pt-8 pb-4">
        <div className="relative flex items-center gap-2 rounded-lg border border-border/60 bg-background px-4 py-3 focus-within:border-accent/50 transition-colors">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleAsk()
              }
            }}
            placeholder={t('sidebar:ask.placeholder', { defaultValue: '输入你的问题…' })}
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground/50"
          />
        </div>
      </div>

      {/* 大家常问 */}
      <div className="px-8 pb-3">
        <span className="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">
          {t('sidebar:ask.popular', { defaultValue: '大家常问' })}
        </span>
      </div>
      <div className="px-8 pb-6 flex flex-wrap gap-2">
        {SUGGESTED_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => handleSuggestionClick(q)}
            className="rounded-full border border-border/40 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:border-accent/40 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* 最近问答 */}
      <div className="px-8 pb-2">
        <span className="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">
          {t('sidebar:ask.recent', { defaultValue: '最近问答' })}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto px-8 pb-8">
        {recentQA.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-center">
              <MessageSquare className="h-8 w-8 text-muted-foreground/30" aria-hidden />
              <p className="text-sm text-muted-foreground/50">
                {t('sidebar:ask.empty', { defaultValue: '还没有问答记录，输入问题开始吧' })}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {recentQA.map((qa) => (
              <div
                key={qa.id}
                className="rounded-lg border border-border/40 p-3 hover:border-border/60 transition-colors"
              >
                <p className="text-sm font-medium text-foreground">{qa.question}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

AskPage.displayName = 'AskPage'
