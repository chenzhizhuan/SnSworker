/**
 * AskPage — 问一句页面（轻量即时问答入口）。
 *
 * 定位：办件事的精简版。该有的都有——模型问答、流式输出、
 * 最近问答历史（localStorage）、大家常问快捷入口、追问续聊，
 * 只是面向"一次一问一答"的轻场景，不建任务、不产出交付物。
 *
 * 问答通道：LocalAgentClient.stream（与 Tin runAgent 同款一次性 session 模式）：
 *   - 合成 `ask-<uuid>` 一次性 sessionId，不污染任务会话、不落后端 session 表
 *   - 流式收集 assistant delta，实时渲染到回答区
 *   - 每条记录独立成答；「继续问」把该条历史问题/回答作为上下文带入下一轮
 *   - 需要 Agent 执行多步任务时，引导去「办件事」
 */

import React, { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageSquare, Search, Send, ArrowRight, RotateCcw, Trash2 } from 'lucide-react'
import { useSpaceStore } from '@stores/useSpaceStore'
import { useOrganizationStore } from '@stores/useOrganizationStore'
import { useAuthStore } from '@stores/useAuthStore'
import { useMainNavStore } from '@stores/useMainNavStore'
import { getLocalAgentClient } from '@/services/localAgentClient'
import { resolvePersonalRulesForRuntime } from '@/services/personalRulesRuntimeCache'
import { cn } from '@utils/cn'

interface RecentQA {
  id: string
  question: string
  answer: string
  timestamp: number
  /** 本轮是否仍在生成中（页面卸载后落盘时清零） */
  pending?: boolean
  /** 生成失败的错误信息 */
  error?: string
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
    return (JSON.parse(raw) as RecentQA[]).map((qa) => ({
      ...qa,
      pending: false, // 恢复时不再有进行中的生成
    }))
  } catch {
    return []
  }
}

function saveRecentQA(list: RecentQA[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(
      list.slice(0, MAX_RECENT).map(({ pending: _pending, ...rest }) => rest),
    ))
  } catch {
    // ignore
  }
}

/** 问一句专用一次性 session（与 chat session UUID、tin-runagent-* 均隔离） */
function makeAskSessionId(): string {
  const uuid =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`
  return `ask-${uuid}`
}

export const AskPage: React.FC = () => {
  const { t } = useTranslation(['sidebar'])
  const [input, setInput] = useState('')
  const [recentQA, setRecentQA] = useState<RecentQA[]>(() => loadRecentQA())
  const [asking, setAsking] = useState(false)
  const [thinkingText, setThinkingText] = useState('')
  const abortRef = useRef<(() => void) | null>(null)
  const answerScrollRef = useRef<HTMLDivElement | null>(null)

  // 组件卸载时中断进行中的问答
  useEffect(() => {
    return () => {
      abortRef.current?.()
      abortRef.current = null
    }
  }, [])

  const persistQA = useCallback((list: RecentQA[]) => {
    setRecentQA(list)
    saveRecentQA(list)
  }, [])

  const askQuestion = useCallback(async (question: string, priorQ?: string, priorA?: string) => {
    const trimmed = question.trim()
    if (!trimmed || asking) return

    const id = `qa-${Date.now()}`
    const entry: RecentQA = { id, question: trimmed, answer: '', timestamp: Date.now(), pending: true }
    const next = [entry, ...recentQA]
    persistQA(next)
    setInput('')
    setAsking(true)

    const localClient = getLocalAgentClient()
    const sessionId = makeAskSessionId()
    const spaceState = useSpaceStore.getState()
    const currentAgent = spaceState?.selectedAgent
    const capturedSpaceId = spaceState?.selectedSpace?.id ?? null
    const authUserId = useAuthStore.getState().user?.id
    const authOwnerKey = authUserId != null ? String(authUserId) : 'anonymous'
    const agentOwnerKey = currentAgent?.user_id != null ? String(currentAgent.user_id) : authOwnerKey
    const canFallbackToCurrentUserProfileRules =
      currentAgent?.user_id == null || String(currentAgent.user_id) === authOwnerKey

    let collected = ''
    let aborted = false
    abortRef.current = () => {
      aborted = true
      try { localClient.abort(sessionId) } catch { /* best-effort */ }
    }

    try {
      const personalRulesForRuntime = await resolvePersonalRulesForRuntime(
        currentAgent,
        agentOwnerKey,
        { allowApiFallback: canFallbackToCurrentUserProfileRules },
      )

      // 有上下文追问时，把上一轮问答作为对话前缀给模型
      const prompt = priorQ && priorA
        ? `【上一轮问答】\n问：${priorQ}\n答：${priorA}\n\n【本轮问题】\n${trimmed}`
        : trimmed

      await localClient.stream(
        sessionId,
        prompt,
        {
          onChunk: (delta: string) => {
            collected += delta
            setRecentQA((prev) => prev.map((qa) =>
              qa.id === id ? { ...qa, answer: collected } : qa,
            ))
          },
          onMessage: () => { /* 一次性问答不处理 HITL / tool 事件 */ },
          onDone: () => { /* 文本已在 onChunk 聚合 */ },
          onError: () => { /* 统一走下方 catch */ },
        },
        {
          agentId: currentAgent?.id,
          yoloMode: useOrganizationStore.getState().selectedOrganization?.settings?.allow_member_yolo === true,
          customRules: currentAgent?.custom_rules,
          personalRules: personalRulesForRuntime,
          agentMode: 'ask', // 纯问答模式：不执行工具、多轮任务
          appContext: capturedSpaceId ? { spaceId: capturedSpaceId } : undefined,
        },
      )

      const answer = collected.trim()
      setRecentQA((prev) => {
        const updated = prev.map((qa) =>
          qa.id === id
            ? {
                ...qa,
                answer: answer || t('sidebar:ask.noAnswer', { defaultValue: '（本轮未产出内容）' }),
                pending: false,
              }
            : qa,
        )
        saveRecentQA(updated)
        return updated
      })
    } catch (err) {
      if (aborted) {
        setRecentQA((prev) => {
          const updated = prev.map((qa) =>
            qa.id === id ? { ...qa, pending: false, answer: qa.answer || '' } : qa,
          )
          saveRecentQA(updated)
          return updated
        })
      } else {
        const message = err instanceof Error ? err.message : String(err)
        setRecentQA((prev) => {
          const updated = prev.map((qa) =>
            qa.id === id ? { ...qa, pending: false, error: message } : qa,
          )
          saveRecentQA(updated)
          return updated
        })
      }
    } finally {
      abortRef.current = null
      setAsking(false)
      setThinkingText('')
    }
  }, [asking, recentQA, persistQA, t])

  const handleAsk = useCallback(() => {
    const question = input.trim()
    if (!question || asking) return
    void askQuestion(question)
  }, [input, asking, askQuestion])

  /** 点击历史记录 → 带上下文追问 */
  const handleFollowUp = useCallback((qa: RecentQA) => {
    if (asking || !qa.question) return
    setInput(`${qa.question} 的后续：`)
    answerScrollRef.current?.scrollTo({ top: 0 })
  }, [asking])

  const handleSuggestionClick = useCallback((q: string) => {
    setInput(q)
  }, [])

  const handleClearHistory = useCallback(() => {
    persistQA([])
  }, [persistQA])

  const goToTasks = useCallback(() => {
    // 办件事 = 主导航 'agent' tab（ContentArea 按 currentTab 渲染任务工作台）。
    // 'tasks' 是 ActivityRail 域 id，不是 MainNavTab——直接 setCurrentTab('tasks')
    // 会被 useMainNavStore 静默拒绝，页面纹丝不动。
    useMainNavStore.getState().setCurrentTab('agent')
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
          {asking ? (
            <button
              type="button"
              onClick={() => abortRef.current?.()}
              className="flex shrink-0 items-center gap-1 rounded-md border border-border/40 px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" aria-hidden />
              {t('sidebar:ask.stop', { defaultValue: '停止' })}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleAsk}
              disabled={!input.trim()}
              className="flex shrink-0 items-center gap-1 rounded-md bg-accent px-2.5 py-1 text-xs text-accent-foreground transition-opacity disabled:opacity-40"
            >
              <Send className="h-3.5 w-3.5" aria-hidden />
              {t('sidebar:ask.send', { defaultValue: '提问' })}
            </button>
          )}
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
      <div className="px-8 pb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">
          {t('sidebar:ask.recent', { defaultValue: '最近问答' })}
        </span>
        {recentQA.length > 0 && (
          <button
            type="button"
            onClick={handleClearHistory}
            className="flex items-center gap-1 text-xs text-muted-foreground/60 hover:text-foreground transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden />
            {t('sidebar:ask.clear', { defaultValue: '清空' })}
          </button>
        )}
      </div>
      <div ref={answerScrollRef} className="flex-1 overflow-y-auto px-8 pb-8">
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
                className="rounded-lg border border-border/40 p-4 hover:border-border/60 transition-colors"
              >
                <p className="text-sm font-medium text-foreground">{qa.question}</p>
                {qa.pending ? (
                  <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
                    <span className="block h-3 w-3 rounded-full border-2 border-border border-t-accent animate-spin" />
                    {thinkingText || t('sidebar:ask.thinking', { defaultValue: '正在思考…' })}
                  </p>
                ) : qa.error ? (
                  <div className="mt-2 space-y-1.5">
                    <p className="text-sm text-red-500/80">
                      {t('sidebar:ask.error', { defaultValue: '回答失败' })}：{qa.error}
                    </p>
                    <button
                      type="button"
                      onClick={() => askQuestion(qa.question)}
                      className="flex items-center gap-1 text-xs text-accent hover:underline"
                    >
                      <RotateCcw className="h-3 w-3" aria-hidden />
                      {t('sidebar:ask.retry', { defaultValue: '重试' })}
                    </button>
                  </div>
                ) : qa.answer ? (
                  <div className="mt-2">
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">{qa.answer}</p>
                    <div className="mt-2 flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => handleFollowUp(qa)}
                        className="flex items-center gap-1 text-xs text-muted-foreground/70 hover:text-foreground transition-colors"
                      >
                        <ArrowRight className="h-3 w-3" aria-hidden />
                        {t('sidebar:ask.followUp', { defaultValue: '继续问' })}
                      </button>
                      <button
                        type="button"
                        onClick={goToTasks}
                        className="flex items-center gap-1 text-xs text-muted-foreground/70 hover:text-foreground transition-colors"
                      >
                        <ArrowRight className="h-3 w-3" aria-hidden />
                        {t('sidebar:ask.goTasks', { defaultValue: '去办件事执行' })}
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

AskPage.displayName = 'AskPage'
