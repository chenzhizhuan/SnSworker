/**
 * AskPage — 问一句页面（轻量即时问答入口）。
 *
 * 定位：办件事工作台的纯问答精简版。复用 ChatPanel 受控渲染完整工作台体验
 * （markdown / 代码高亮 / HITL 卡片 / 流式输出 / 停止 / 重试），但：
 *   - 会话池独立：agent_mode='ask'，与办件事会话天然隔离；
 *   - 只保留问答：隐藏附件 / Skill / MCP / Agent 身份入口（askOnlyAgent）；
 *   - 模型选择保留。
 *
 * 结构（薄壳）：
 *   - 顶部：自管 ask 会话历史列表（直接调 chat-client 拉 agent_mode='ask'，
 *     不走 store loadSessions，避免共享桶互相覆盖）；
 *   - 主区：ChatPanel controlledSessionId 受控嵌入（不碰全局指针 / 共享桶指针）。
 *
 * 会话生命周期：
 *   - 首问：AskPage 自己 ensureSessionForSpace（attachOnly + agentMode:'ask'）
 *     → setSessionAgentMode('ask') → sendMessage，随后 setActiveSessionId；
 *   - 追问 / 停止 / 重试：ChatPanel 内部回调（受控 currentSessionId 短路全局指针）；
 *   - 历史会话：点击后 loadSessionMessages hydrate → setActiveSessionId。
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageSquare, Search, Send, Trash2, Plus } from 'lucide-react'
import { useSpaceStore } from '@stores/useSpaceStore'
import { useOrganizationStore } from '@stores/useOrganizationStore'
import { useChatStore } from '@stores/chat/useChatStore'
import { isSessionBusy } from '@stores/chat/execution/sessionRunProjection'
import { setSessionAgentMode } from '@stores/chat/session/sessionAgentMode'
import { resolveChatSessionListQuery } from '@stores/chat/session/utils/chatSessionScope'
import { ChatPanel } from '@components/chat/panel/ChatPanel'
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

export const AskPage: React.FC = () => {
  const { t } = useTranslation(['sidebar'])
  const [history, setHistory] = useState<AskHistoryEntry[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [sending, setSending] = useState(false)
  const [input, setInput] = useState('')

  // 当前选中 space / 组织
  const spaceId = useSpaceStore(s => s.selectedSpace?.id ?? null)
  const selectedSpace = useSpaceStore(s => s.selectedSpace)
  const organizationId = useOrganizationStore(s => s.selectedOrganization?.id ?? null)

  // ── 历史 ask 会话列表（自管，不走共享桶）──
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

  useEffect(() => {
    void refreshHistory()
  }, [refreshHistory])

  // 切换 space 后：当前会话若不属于新 space 的 ask 池，清掉 active 指向
  useEffect(() => {
    if (!activeSessionId) return
    if (!spaceId) {
      setActiveSessionId(null)
      return
    }
    const client = useChatStore.getState()
    const session = client.getSessionById(activeSessionId)
    const belongsToSpace = session
      && (session.space_id === spaceId || session.workspace_id === spaceId)
    const inHistory = history.some(h => h.id === activeSessionId)
    if (!belongsToSpace && !inHistory && !isSessionBusy(activeSessionId)) {
      setActiveSessionId(null)
    }
  }, [spaceId, activeSessionId, history])

  // 组件卸载时中断进行中的问答
  useEffect(() => {
    return () => {
      if (activeSessionId) {
        useChatStore.getState().abortStream(activeSessionId)
      }
    }
  }, [activeSessionId])

  /** 首问：ensure 会话（ask 池）→ 设 agent mode → 发送 → 激活会话 */
  const handleFirstSend = useCallback(async (question: string) => {
    const trimmed = question.trim()
    if (!trimmed || sending) return
    if (!spaceId || !organizationId) {
      console.warn('[AskPage] Missing space / organization, skip send')
      return
    }

    setSending(true)
    setInput('')
    try {
      // 创建 ask 会话：attachOnly 不污染办件事指针
      const result = await useChatStore.getState().ensureSessionForSpace(
        spaceId,
        organizationId,
        undefined,
        {
          trigger: 'pre_send',
          preferQuickStart: true,
          agentMode: 'ask',
          attachOnly: true,
        },
      )
      const sessionId = result.sessionId

      // 确保运行时按 ask 模式运行（纯问答、不执行工具）
      setSessionAgentMode(sessionId, 'ask')
      setActiveSessionId(sessionId)

      // 发送消息（消息直接进 store 消息桶，ChatPanel 受控渲染立即可见）
      await useChatStore.getState().sendMessage(
        trimmed,
        true,
        undefined,
        undefined,
        sessionId,
        { spaceId },
      )

      // 刷新历史列表（新会话入列）
      void refreshHistory()
    } catch (err) {
      console.error('[AskPage] handleFirstSend failed:', err)
    } finally {
      setSending(false)
    }
  }, [sending, spaceId, organizationId, refreshHistory])

  /** 点击历史会话 → hydrate 消息 → 激活 */
  const handleSelectHistory = useCallback(async (sessionId: string) => {
    if (isSessionBusy(sessionId)) return
    setActiveSessionId(sessionId)
    const cached = useChatStore.getState().messagesBySessionId[sessionId]
    if (cached === undefined) {
      await useChatStore.getState().loadSessionMessages(sessionId)
    }
  }, [])

  /** 新问答：回到欢迎输入态 */
  const handleNewAsk = useCallback(() => {
    if (activeSessionId && isSessionBusy(activeSessionId)) return
    setActiveSessionId(null)
    setInput('')
  }, [activeSessionId])

  /** 删除单条 ask 会话 */
  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      const client = getChatClient()
      await client.sessions.delete(sessionId)
      setHistory(prev => prev.filter(h => h.id !== sessionId))
      if (activeSessionId === sessionId) setActiveSessionId(null)
    } catch (err) {
      console.warn('[AskPage] deleteSession failed:', err)
    }
  }, [activeSessionId])

  /** 清空全部 ask 会话 */
  const handleClearHistory = useCallback(async () => {
    try {
      const client = getChatClient()
      for (const entry of history) {
        await client.sessions.delete(entry.id)
      }
      setHistory([])
      if (activeSessionId) {
        useChatStore.getState().abortStream(activeSessionId)
        setActiveSessionId(null)
      }
    } catch (err) {
      console.warn('[AskPage] clearHistory failed:', err)
    }
  }, [history, activeSessionId])

  // ChatPanel 所需 spaceContext：直接用 selectedSpace（满足 SpaceContext 结构）
  const spaceContext = useMemo(() => {
    if (!selectedSpace) return null
    return {
      id: selectedSpace.id,
      name: selectedSpace.name,
      organization_id: selectedSpace.organization_id,
      ...(selectedSpace.agent_id != null ? { agent_id: selectedSpace.agent_id } : {}),
      ...(selectedSpace.config_version != null ? { config_version: selectedSpace.config_version } : {}),
      ...(selectedSpace.suggested_prompts ? { suggested_prompts: selectedSpace.suggested_prompts } : {}),
    }
  }, [selectedSpace])

  return (
    <div className="flex h-full w-full overflow-hidden">
      {/* 左侧：ask 会话列表 */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-border/40 bg-background/40">
        {/* 新问答按钮 */}
        <div className="p-3">
          <button
            type="button"
            onClick={handleNewAsk}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-accent/40 bg-accent/10 px-3 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent/20"
          >
            <Plus className="h-4 w-4" aria-hidden />
            {t('sidebar:ask.newAsk', { defaultValue: '新问答' })}
          </button>
        </div>

        {/* 历史列表 */}
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex items-center justify-between px-4 pb-1.5">
            <span className="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">
              {t('sidebar:ask.recent', { defaultValue: '最近问答' })}
            </span>
            {history.length > 0 && (
              <button
                type="button"
                onClick={() => void handleClearHistory()}
                className="flex items-center gap-1 text-xs text-muted-foreground/60 hover:text-foreground transition-colors"
                title={t('sidebar:ask.clear', { defaultValue: '清空' })}
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden />
              </button>
            )}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
            {loadingHistory && history.length === 0 ? (
              <div className="flex h-20 items-center justify-center">
                <span className="block h-5 w-5 rounded-full border-2 border-border border-t-accent animate-spin" />
              </div>
            ) : history.length === 0 ? (
              <div className="flex h-20 flex-col items-center justify-center gap-1.5 text-center">
                <MessageSquare className="h-6 w-6 text-muted-foreground/30" aria-hidden />
                <p className="text-xs text-muted-foreground/50">
                  {t('sidebar:ask.empty', { defaultValue: '还没有问答记录' })}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {history.map(entry => (
                  <div
                    key={entry.id}
                    className={`group flex items-center gap-1 rounded-md px-2 py-1.5 text-sm transition-colors ${
                      entry.id === activeSessionId
                        ? 'bg-accent/10 text-accent'
                        : 'text-foreground/80 hover:bg-background/80'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => void handleSelectHistory(entry.id)}
                      className="flex-1 truncate text-left"
                      title={entry.title}
                    >
                      {entry.title}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteSession(entry.id)}
                      className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-500"
                      title={t('sidebar:ask.deleteSession', { defaultValue: '删除' })}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* 右侧主区：ChatPanel 受控渲染 or 欢迎输入态 */}
      <main className="relative min-w-0 flex-1">
        {activeSessionId ? (
          <ChatPanel
            isActive
            variant="embedded"
            hideSessionTabs
            showInlineHistory={false}
            showInlineNewTopicButton={false}
            spaceContext={spaceContext}
            organizationId={organizationId}
            controlledSessionId={activeSessionId}
            tabScopeKeyOverride={`ask:${spaceId ?? 'default'}`}
            askOnlyAgent
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center px-8">
            <div className="w-full max-w-2xl">
              <h1 className="mb-6 text-center text-2xl font-semibold tracking-tight text-foreground">
                {t('sidebar:ask.welcomeTitle', { defaultValue: '问一句，马上得到答案' })}
              </h1>
              <div className="relative flex items-center gap-2 rounded-lg border border-border/60 bg-background px-4 py-3 focus-within:border-accent/50 transition-colors">
                <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      void handleFirstSend(input)
                    }
                  }}
                  placeholder={t('sidebar:ask.placeholder', { defaultValue: '输入你的问题…' })}
                  className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground/50"
                />
                <button
                  type="button"
                  onClick={() => void handleFirstSend(input)}
                  disabled={!input.trim() || sending}
                  className="flex shrink-0 items-center gap-1 rounded-md bg-accent px-2.5 py-1 text-xs text-accent-foreground transition-opacity disabled:opacity-40"
                >
                  <Send className="h-3.5 w-3.5" aria-hidden />
                  {t('sidebar:ask.send', { defaultValue: '提问' })}
                </button>
              </div>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setInput(q)}
                    className="rounded-full border border-border/40 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:border-accent/40 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

AskPage.displayName = 'AskPage'
