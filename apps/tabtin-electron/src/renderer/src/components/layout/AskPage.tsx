/**
 * AskPage — 问一句页面（轻量即时问答入口）。
 *
 * 定位：办件事工作台的纯问答精简版。复用 ChatPanel 受控渲染完整工作台体验
 * （markdown / 代码高亮 / HITL 卡片 / 流式输出 / 停止 / 重试），但：
 *   - 会话池独立：agent_mode='ask'，与办件事会话天然隔离；
 *   - 专属工作空间：provisioning_source='system_ask'，侧栏自动隐藏、办件事不可见；
 *   - 只保留问答：隐藏附件 / Skill / MCP / Agent 身份入口（askOnlyAgent）；
 *   - 模型选择保留。
 *
 * 结构（薄壳）：
 *   - 启动：自动调 ensureAsk 获取/创建问一句专属工作空间（幂等）；
 *   - 顶部：自管 ask 会话历史列表（直接调 chat-client 拉 agent_mode='ask'，
 *     不走 store loadSessions，避免共享桶互相覆盖）；
 *   - 主区：ChatPanel controlledSessionId 受控嵌入（不碰全局指针 / 共享桶指针）。
 *
 * 会话生命周期：
 *   - 新问答：点击按钮时先决策（askNewSessionTargetPolicy）：
 *     ① 当前激活会话本身就是空白 → 停在原地，不新建不切换；
 *     ② 否则优先复用最近一个空白 ask 会话（单槽，避免堆空行）；
 *     ③ 仅当无任何空白会话时才 createSession（agentMode:'ask'，attachOnly）
 *     并自动激活；创建中按钮禁用防连点；
 *   - 追问 / 停止 / 重试：ChatPanel 内部回调（受控 currentSessionId 短路全局指针）；
 *   - 历史会话：点击后 loadSessionMessages hydrate → setActiveSessionId；
 *   - 兑底：任何路径（含删除/清空）后 activeSessionId 为空时，若 store 内仍有
 *     ask 会话则自动绑定最近一个，保证 ChatPanel 永远有可用的受控会话。
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageSquare, Trash2, Plus, RefreshCw } from 'lucide-react'
import { useOrganizationStore } from '@stores/useOrganizationStore'
import { useDeviceStore } from '@stores/useDeviceStore'
import { useChatStore } from '@stores/chat/useChatStore'
import { isSessionBusy } from '@stores/chat/execution/sessionRunProjection'
import { resolveChatSessionListQuery } from '@stores/chat/session/utils/chatSessionScope'
import { ChatPanel } from '@components/chat/panel/ChatPanel'
import {
  decideAskNewSessionTarget,
  type AskSessionLike,
} from '@components/layout/askNewSessionTargetPolicy'
import { getChatClient } from '@/services/chatApi'
import type { ChatSession } from '@tabtin/chat-client'
import { WorkspaceApiService } from '@tabtin/app-shell'
import type { WorkspaceSummary } from '@tabtin/app-shell'
import { createLogger } from '@/utils/logger'

const log = createLogger('AskPage')

/** 问一句历史会话列表条目（精简版，只含列表展示所需） */
interface AskHistoryEntry {
  id: string
  title: string
  last_message_at: string | null
  message_count: number | null
}

/** 稳定空引用：zustand 5 selector 不可返回新数组（getSnapshot 死循环） */
const EMPTY_ASK_SESSIONS: ChatSession[] = []

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
  const [creatingSession, setCreatingSession] = useState(false)
  const [askWorkspace, setAskWorkspace] = useState<WorkspaceSummary | null>(null)
  const [workspaceLoading, setWorkspaceLoading] = useState(true)
  const [workspaceError, setWorkspaceError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const organizationId = useOrganizationStore(s => s.selectedOrganization?.id ?? null)
  const organizationName = useOrganizationStore(s => s.selectedOrganization?.name ?? '')
  const deviceId = useDeviceStore(s => s.currentDevice?.id ?? null)

  // ── 幂等获取/创建问一句专属工作空间 ──
  // 失败后展示错误态并提供「重试」按钮（reloadKey 变化重新触发本 effect）
  useEffect(() => {
    if (!organizationId || !deviceId) return
    let cancelled = false
    setWorkspaceLoading(true)
    setWorkspaceError(null)
    void (async () => {
      try {
        // 获取问一句专属目录（与 home 类似但独立命名）
        const dirResult = await window.tabtin?.fileSystem?.ensureDefaultAgentDir({
          organizationName,
          spaceName: '问一句',
        })
        if (!dirResult?.success || !dirResult.path) {
          log.warn('ensureDefaultAgentDir failed for ask workspace:', dirResult?.error ?? 'no path')
          if (!cancelled) setWorkspaceError('ensureDefaultAgentDir failed')
          return
        }
        if (cancelled) return
        const workspace = await WorkspaceApiService.ensureAsk({
          organization_id: organizationId,
          device_id: deviceId,
          working_dir: dirResult.path,
          working_dir_type: 'mixed',
          name: '问一句工作空间',
        })
        if (cancelled) return
        setAskWorkspace(workspace)
      } catch (err) {
        log.warn('ensureAsk failed:', err instanceof Error ? err.message : String(err))
        if (!cancelled) {
          setWorkspaceError(err instanceof Error ? err.message : String(err))
        }
      } finally {
        if (!cancelled) setWorkspaceLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [organizationId, organizationName, deviceId, reloadKey])

  const handleRetryWorkspace = useCallback(() => {
    setReloadKey(k => k + 1)
  }, [])

  const spaceId = askWorkspace?.id ?? null

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

  // ── 标题自动刷新：订阅 store 中 ask 会话的 title 变化 ──
  // WS agent.user.title_updated 只更新 store 的 sessionsBySpaceId 桶，
  // AskPage 的 history 是局部 state 收不到通知。这里通过订阅 store 变化同步标题。
  // 注意：zustand 5 selector 必须返回稳定引用——不得在 selector 内 filter/map
  // 出新数组（会触发 getSnapshot 死循环，见 useWsConnectionStatus.snapshot-stability.test.tsx）。
  // 因此先订整个桶引用，再在 useMemo 里派生 ask 会话。
  const askSpaceBucket = useChatStore(s =>
    spaceId ? (s.sessionsBySpaceId[spaceId] ?? null) : null,
  )
  const storeAskSessions = useMemo(() => {
    if (!askSpaceBucket) return EMPTY_ASK_SESSIONS
    return askSpaceBucket.filter(sess => sess.agent_mode === 'ask')
  }, [askSpaceBucket])
  useEffect(() => {
    if (storeAskSessions.length === 0 || history.length === 0) return
    let changed = false
    const updated = history.map(entry => {
      const storeSession = storeAskSessions.find(s => s.id === entry.id)
      if (storeSession && storeSession.title && storeSession.title !== entry.title) {
        changed = true
        return { ...entry, title: storeSession.title }
      }
      return entry
    })
    if (changed) {
      setHistory(updated)
    }
  }, [storeAskSessions, history])

  // ── 自动收口：activeSessionId 为 null 时，若有新 ask 会话进入 store
  // （含 handleNewAsk 点击即创建后的新会话），自动绑定到最近一个，
  // 使 ChatPanel controlledSessionId 始终指向有效会话。 ──
  useEffect(() => {
    if (activeSessionId || !spaceId || storeAskSessions.length === 0) return
    // 找最近的 ask 会话（按 last_message_at 降序，无则取第一个）
    const latest = storeAskSessions
      .filter(s => (s.space_id === spaceId || s.workspace_id === spaceId))
      .sort((a, b) => {
        const ta = a.last_message_at ? new Date(a.last_message_at).getTime() : 0
        const tb = b.last_message_at ? new Date(b.last_message_at).getTime() : 0
        return tb - ta
      })[0]
    if (latest) {
      setActiveSessionId(latest.id)
      void refreshHistory()
    }
  }, [activeSessionId, spaceId, storeAskSessions, refreshHistory])

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

  // ── 「新问答」决策池：store 桶 ∪ history ──
  // store 桶：新会话创建时实时写入，has_messages 字段权威；
  // history：服务器全量列表——重启后 store 桶可能为空，仅看 store 会误判
  // 「无空白会话」而堆新建。合并去重，store 命中优先（更新鲜）。
  const askDecisionPool = useMemo<AskSessionLike[]>(() => {
    const byId = new Map<string, AskSessionLike>()
    for (const entry of history) {
      // history 查询本身已按 status:'active' + agent_mode:'ask' 过滤
      byId.set(entry.id, {
        id: entry.id,
        status: 'active',
        agent_mode: 'ask',
        message_count: entry.message_count,
        last_message_at: entry.last_message_at,
      })
    }
    for (const s of storeAskSessions) {
      byId.set(s.id, s)
    }
    return Array.from(byId.values())
  }, [history, storeAskSessions])

  // 组件卸载时中断进行中的问答
  useEffect(() => {
    return () => {
      if (activeSessionId) {
        useChatStore.getState().abortStream(activeSessionId)
      }
    }
  }, [activeSessionId])

  /** 点击历史会话 → hydrate 消息 → 激活 */
  const handleSelectHistory = useCallback(async (sessionId: string) => {
    if (isSessionBusy(sessionId)) return
    setActiveSessionId(sessionId)
    const cached = useChatStore.getState().messagesBySessionId[sessionId]
    if (cached === undefined) {
      await useChatStore.getState().loadSessionMessages(sessionId)
    }
  }, [])

  /** 新问答：空白不堆积——active 空白停在原地，否则复用最近空白，无空白才新建 */
  const handleNewAsk = useCallback(async () => {
    if (creatingSession) return
    if (activeSessionId && isSessionBusy(activeSessionId)) return
    if (!spaceId || !organizationId) {
      console.warn('[AskPage] handleNewAsk: spaceId 或 organizationId 为空，跳过创建')
      return
    }

    // 决策：当前会话已空白 → 不动；有空白可复用 → 激活它；否则才新建
    const decision = decideAskNewSessionTarget({
      activeSessionId,
      askSessions: askDecisionPool,
    })
    if (decision.action === 'keep_active') return
    if (decision.action === 'reuse_empty') {
      const targetId = decision.sessionId
      // 复用前需确认目标不在运行中（如另一个空会话正被流式写入首答）
      if (!isSessionBusy(targetId)) {
        setActiveSessionId(targetId)
        const cached = useChatStore.getState().messagesBySessionId[targetId]
        if (cached === undefined) {
          await useChatStore.getState().loadSessionMessages(targetId)
        }
      }
      return
    }

    setCreatingSession(true)
    try {
      const sessionId = await useChatStore.getState().createSession(
        spaceId,
        organizationId,
        undefined,
        { trigger: 'explicit', activate: false, agentMode: 'ask' },
      )
      if (sessionId) {
        setActiveSessionId(sessionId)
        void refreshHistory()
      }
    } catch (err) {
      console.warn('[AskPage] handleNewAsk failed:', err)
    } finally {
      setCreatingSession(false)
    }
  }, [activeSessionId, askDecisionPool, creatingSession, organizationId, refreshHistory, spaceId])

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

  // ChatPanel 所需 spaceContext：用 ask 专属工作空间构造
  const spaceContext = useMemo(() => {
    if (!askWorkspace) return null
    return {
      id: askWorkspace.id,
      name: askWorkspace.name,
      organization_id: askWorkspace.organization_id,
      ...(askWorkspace.agent_id != null ? { agent_id: askWorkspace.agent_id } : {}),
    }
  }, [askWorkspace])

  // 工作空间加载中：显示骨架屏
  if (workspaceLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <span className="block h-6 w-6 rounded-full border-2 border-border border-t-accent animate-spin" />
      </div>
    )
  }

  // 工作空间获取失败：显示错误提示 + 重试按钮
  if (!askWorkspace) {
    return (
      <div className="flex h-full w-full items-center justify-center px-8">
        <div className="text-center">
          <p className="text-sm text-muted-foreground">
            {t('sidebar:ask.workspaceError', { defaultValue: '问一句工作空间初始化失败，请稍后重试' })}
          </p>
          {workspaceError ? (
            <p className="mt-1 text-xs text-muted-foreground/50">{workspaceError}</p>
          ) : null}
          <button
            type="button"
            onClick={handleRetryWorkspace}
            className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-border/40 px-3 py-1.5 text-sm text-foreground hover:border-accent/40 hover:text-accent transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden />
            {t('common:retry', { defaultValue: '重试' })}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full w-full overflow-hidden">
      {/* 左侧：ask 会话列表 */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-border/40 bg-background/40">
        {/* 新问答按钮 */}
        <div className="p-3">
          <button
            type="button"
            onClick={() => void handleNewAsk()}
            disabled={creatingSession}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-accent/40 bg-accent/10 px-3 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {creatingSession ? (
              <span className="block h-4 w-4 animate-spin rounded-full border-2 border-border border-t-accent" aria-hidden />
            ) : (
              <Plus className="h-4 w-4" aria-hidden />
            )}
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

        {/* 右侧主区：ChatPanel 始终渲染（含草稿态），去掉欢迎页 */}
      <main className="relative min-w-0 flex-1">
          <ChatPanel
            isActive
            variant="embedded"
            hideSessionTabs
            showInlineHistory={false}
            showInlineNewTopicButton={false}
            spaceContext={spaceContext}
            organizationId={organizationId}
            controlledSessionId={activeSessionId ?? undefined}
            tabScopeKeyOverride={`ask:${spaceId ?? 'default'}`}
            askOnlyAgent
          />
      </main>
    </div>
  )
}

AskPage.displayName = 'AskPage'
