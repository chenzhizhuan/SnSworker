/**
 * AskPage — 问一句页面（轻量即时问答入口）。
 *
 * 定位：办件事的精简版。复用 useChatStore 会话闭环（流式回答、停止/重试、
 * 历史列表服务端持久化、追问带上下文），但用独立会话池（agent_mode='ask'）
 * 与办件事会话天然隔离。
 *
 * 会话隔离方案：
 *   - 创建会话时传 agentMode='ask'，后端 ChatSession.agent_mode='ask'
 *   - 列表请求传 agent_mode='ask' 过滤，只看问句会话
 *   - 办件事列表不传过滤（看全部），互不干扰
 *   - 不走 store loadSessions（共享桶会互相覆盖），直接调 chat-client 拉列表
 *
 * 渲染层：自渲染消息壳（不依赖 ChatPanel 布局）
 *   - messagesBySessionId[sessionId] 过滤 user/assistant 消息
 *   - useStreamingContent(sessionId, messageId) 拿流式增量
 *
 * 运行时操作走 useChatStore：
 *   - sendMessage / abortStream / continueAgentAfterError
 *   - ensureSessionForSpace（attachOnly:true 避免污染办件事指针）
 *   - setSessionAgentMode(sessionId, 'ask') 确保按 ask 模式运行
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageSquare, Search, Send, ArrowRight, RotateCcw, Trash2 } from 'lucide-react'
import { useSpaceStore } from '@stores/useSpaceStore'
import { useOrganizationStore } from '@stores/useOrganizationStore'
import { useMainNavStore } from '@stores/useMainNavStore'
import { useChatStore } from '@stores/chat/useChatStore'
import { useSessionBusy, isSessionBusy } from '@stores/chat/execution/sessionRunProjection'
import { useStreamingContent } from '@stores/chat/execution/streamingContent'
import { setSessionAgentMode } from '@stores/chat/session/sessionAgentMode'
import { continueAgentAfterError } from '@stores/chat/messages/actions/continueAgentAfterError'
import { resolveChatSessionListQuery } from '@stores/chat/session/utils/chatSessionScope'
import { getChatClient } from '@/services/chatApi'
import type { ChatSession } from '@tabtin/chat-client'

const SUGGESTED_QUESTIONS = [
  '如何创建工作空间？',
  '怎么导入外部数据？',
  '技能和连接器有什么区别？',
  '如何分享文档给团队成员？',
]

/** 问一句历史会话列表条目（精简版，只含列表展示所需） */
interface AskHistoryEntry {
  id: string
  title: string
  last_message_at: string | null
  message_count: number | null
}

/** 从 ChatSession 列表项提取精简展示数据 */
function toHistoryEntry(session: ChatSession): AskHistoryEntry {
  return {
    id: session.id,
    title: session.title || '问一句',
    last_message_at: session.last_message_at ?? null,
    message_count: session.message_count ?? null,
  }
}

/**
 * 单条问答渲染——从 store 按 sessionId 读取消息列表，
 * assistant 最后一条消息用 useStreamingContent 拿流式增量。
 */
const AskQACard: React.FC<{
  sessionId: string
  onSelectSession: (sessionId: string) => void
}> = ({ sessionId, onSelectSession }) => {
  const { t } = useTranslation(['sidebar'])
  const busy = useSessionBusy(sessionId)
  const messages = useChatStore(s => s.messagesBySessionId[sessionId]) ?? []

  // 过滤 user + assistant 消息（跳过 system / tool 消息）
  const visibleMessages = useMemo(
    () => messages.filter(m => m.role === 'user' || m.role === 'assistant'),
    [messages],
  )

  // 找最后一条 assistant 消息用于流式渲染
  const lastAssistantMsg = useMemo(() => {
    for (let i = visibleMessages.length - 1; i >= 0; i--) {
      if (visibleMessages[i].role === 'assistant') return visibleMessages[i]
    }
    return null
  }, [visibleMessages])

  // 流式增量内容
  const streamingContent = useStreamingContent(
    busy ? sessionId : null,
    lastAssistantMsg?.id ?? '',
  )

  // 判断最后一条 assistant 是否有错误
  const hasError = useMemo(() => {
    if (!lastAssistantMsg) return false
    const sr = lastAssistantMsg.stop_reason
    const ei = lastAssistantMsg.error_info_json
    return sr === 'error' || sr === 'timeout' ||
      (ei != null && (ei.aborted !== true && ei.category != null && ei.category !== 'aborted'))
  }, [lastAssistantMsg])

  // 最后一条 user 消息作为问题展示
  const lastUserMsg = useMemo(() => {
    for (let i = visibleMessages.length - 1; i >= 0; i--) {
      if (visibleMessages[i].role === 'user') return visibleMessages[i]
    }
    return null
  }, [visibleMessages])

  // 渲染 assistant 回答内容：流式优先，否则读消息 content
  const answerText = useMemo(() => {
    if (busy && streamingContent != null) return streamingContent
    if (lastAssistantMsg) return lastAssistantMsg.content || ''
    return ''
  }, [busy, streamingContent, lastAssistantMsg])

  if (!lastUserMsg) return null

  const questionText = lastUserMsg.content || ''

  return (
    <div
      className="rounded-lg border border-border/40 p-4 hover:border-border/60 transition-colors cursor-pointer"
      onClick={() => onSelectSession(sessionId)}
    >
      <p className="text-sm font-medium text-foreground">{questionText}</p>
      {busy && !answerText ? (
        <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
          <span className="block h-3 w-3 rounded-full border-2 border-border border-t-accent animate-spin" />
          {t('sidebar:ask.thinking', { defaultValue: '正在思考…' })}
        </p>
      ) : hasError && !busy ? (
        <div className="mt-2 space-y-1.5">
          <p className="text-sm text-red-500/80">
            {t('sidebar:ask.error', { defaultValue: '回答失败' })}
          </p>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              void continueAgentAfterError(sessionId)
            }}
            className="flex items-center gap-1 text-xs text-accent hover:underline"
          >
            <RotateCcw className="h-3 w-3" aria-hidden />
            {t('sidebar:ask.retry', { defaultValue: '重试' })}
          </button>
        </div>
      ) : answerText ? (
        <div className="mt-2">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">{answerText}</p>
          {!busy && (
            <div className="mt-2 flex items-center gap-3">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onSelectSession(sessionId)
                }}
                className="flex items-center gap-1 text-xs text-muted-foreground/70 hover:text-foreground transition-colors"
              >
                <ArrowRight className="h-3 w-3" aria-hidden />
                {t('sidebar:ask.followUp', { defaultValue: '继续问' })}
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  useMainNavStore.getState().setCurrentTab('agent')
                }}
                className="flex items-center gap-1 text-xs text-muted-foreground/70 hover:text-foreground transition-colors"
              >
                <ArrowRight className="h-3 w-3" aria-hidden />
                {t('sidebar:ask.goTasks', { defaultValue: '去办件事执行' })}
              </button>
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}

export const AskPage: React.FC = () => {
  const { t } = useTranslation(['sidebar'])
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<AskHistoryEntry[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  // 当前选中 space
  const spaceId = useSpaceStore(s => s.selectedSpace?.id ?? null)
  const organizationId = useOrganizationStore(s => s.selectedOrganization?.id ?? null)

  // 拉取问句会话历史列表
  const refreshHistory = useCallback(async () => {
    if (!spaceId) return
    setLoadingHistory(true)
    try {
      const client = getChatClient()
      const query = resolveChatSessionListQuery(spaceId)
      const response = await client.sessions.list({
        ...query,
        agent_mode: 'ask',
        limit: 50,
        status: 'active',
      })
      const sessions = response?.sessions ?? []
      setHistory(sessions.map(toHistoryEntry))
    } catch (err) {
      console.warn('[AskPage] refreshHistory failed:', err)
    } finally {
      setLoadingHistory(false)
    }
  }, [spaceId])

  // 挂载时拉历史
  useEffect(() => {
    void refreshHistory()
  }, [refreshHistory])

  // 组件卸载时中断进行中的问答
  useEffect(() => {
    return () => {
      if (activeSessionId) {
        useChatStore.getState().abortStream(activeSessionId)
      }
    }
  }, [activeSessionId])

  // 当前是否正在生成（hooks 必须无条件调用，且需在引用前声明）
  const isBusy = useSessionBusy(activeSessionId)

  /** 提问：创建/复用会话 → 设 agent mode → 发送消息 */
  const askQuestion = useCallback(async (question: string, existingSessionId?: string) => {
    const trimmed = question.trim()
    if (!trimmed || sending) return

    if (!spaceId) {
      console.warn('[AskPage] No active space')
      return
    }

    setSending(true)
    setInput('')

    try {
      let sessionId = existingSessionId

      if (!sessionId) {
        // 创建新会话：attachOnly=true 不污染办件事指针
        const result = await useChatStore.getState().ensureSessionForSpace(
          spaceId,
          organizationId ?? undefined,
          undefined,
          {
            trigger: 'pre_send',
            preferQuickStart: true,
            agentMode: 'ask',
            attachOnly: true,
          },
        )
        sessionId = result.sessionId

        // 确保运行时按 ask 模式运行（纯问答、不执行工具）
        setSessionAgentMode(sessionId, 'ask')
      }

      setActiveSessionId(sessionId)

      // 发送消息
      await useChatStore.getState().sendMessage(
        trimmed,
        true,
        undefined,
        undefined,
        sessionId,
        { spaceId },
      )

      // 刷新历史列表
      void refreshHistory()
    } catch (err) {
      console.error('[AskPage] askQuestion failed:', err)
    } finally {
      setSending(false)
    }
  }, [sending, spaceId, organizationId, refreshHistory])

  const handleAsk = useCallback(() => {
    const question = input.trim()
    if (!question || sending || isBusy) return
    void askQuestion(question, activeSessionId ?? undefined)
  }, [input, sending, isBusy, activeSessionId, askQuestion])

  /** 点击历史会话 → 加载消息并设为 active */
  const handleSelectHistory = useCallback(async (sessionId: string) => {
    // 如果正在生成，先停止
    if (isSessionBusy(sessionId)) return

    setActiveSessionId(sessionId)

    // 加载消息到 store（如果尚未加载）
    const cached = useChatStore.getState().messagesBySessionId[sessionId]
    if (cached === undefined) {
      await useChatStore.getState().loadSessionMessages(sessionId)
    }

    scrollRef.current?.scrollTo({ top: 0 })
  }, [])

  /** 继续问：设 active session 后聚焦输入框 */
  const handleFollowUp = useCallback((sessionId: string) => {
    if (isSessionBusy(sessionId)) return
    setActiveSessionId(sessionId)
    // 确保消息已加载
    const cached = useChatStore.getState().messagesBySessionId[sessionId]
    if (cached === undefined) {
      void useChatStore.getState().loadSessionMessages(sessionId)
    }
    scrollRef.current?.scrollTo({ top: 0 })
  }, [])

  const handleSuggestionClick = useCallback((q: string) => {
    setInput(q)
  }, [])

  const handleClearHistory = useCallback(async () => {
    if (!spaceId) return
    try {
      const client = getChatClient()
      // 逐个删除 ask 会话
      for (const entry of history) {
        await client.sessions.delete(entry.id)
      }
      setHistory([])
      setActiveSessionId(null)
    } catch (err) {
      console.warn('[AskPage] clearHistory failed:', err)
    }
  }, [spaceId, history])

  // 停止生成
  const handleStop = useCallback(() => {
    if (activeSessionId) {
      useChatStore.getState().abortStream(activeSessionId)
    }
  }, [activeSessionId])

  // 渲染列表：active session 在最前，其余按历史顺序
  const renderSessionIds = useMemo(() => {
    if (!activeSessionId) return history.map(h => h.id)
    // active session 排第一
    const rest = history.filter(h => h.id !== activeSessionId).map(h => h.id)
    return [activeSessionId, ...rest]
  }, [activeSessionId, history])

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
          {isBusy || sending ? (
            <button
              type="button"
              onClick={handleStop}
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
        {history.length > 0 && (
          <button
            type="button"
            onClick={() => void handleClearHistory()}
            className="flex items-center gap-1 text-xs text-muted-foreground/60 hover:text-foreground transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden />
            {t('sidebar:ask.clear', { defaultValue: '清空' })}
          </button>
        )}
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 pb-8">
        {renderSessionIds.length === 0 && !loadingHistory ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-center">
              <MessageSquare className="h-8 w-8 text-muted-foreground/30" aria-hidden />
              <p className="text-sm text-muted-foreground/50">
                {t('sidebar:ask.empty', { defaultValue: '还没有问答记录，输入问题开始吧' })}
              </p>
            </div>
          </div>
        ) : loadingHistory && history.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <span className="block h-6 w-6 rounded-full border-2 border-border border-t-accent animate-spin" />
          </div>
        ) : (
          <div className="space-y-3">
            {renderSessionIds.map(sid => (
              <AskQACard
                key={sid}
                sessionId={sid}
                onSelectSession={(id) => void handleFollowUp(id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

AskPage.displayName = 'AskPage'
