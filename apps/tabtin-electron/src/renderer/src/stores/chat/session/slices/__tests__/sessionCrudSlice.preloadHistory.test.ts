/**
 * 跨设备历史补全（preloadFullHistory / runHistoryPreload）回归。
 *
 * 锁定：
 * - 无本机 transcript 的会话进入后，后台循环翻页拉到 has_more=false 为止；
 * - in-flight 去重：同会话并发补全只跑一个循环；
 * - hasMore 非 true / 共享会话 / 连续失败达上限时不拉或放弃；
 * - loadSessionMessages 服务端路径 has_more=true 时自动触发补全。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { ChatSession, ChatMessage } from '@tabtin/chat-client'
import { createSessionCrudActions, type SessionCrudStore } from '../sessionCrudSlice'
import { useSessionAccessStore } from '../../sessionAccessStore'

vi.mock('@/utils/logger', () => ({
  logger: { log: vi.fn(), debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  createLogger: () => ({ log: vi.fn(), debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }),
}))
vi.mock('../../../execution/chatTelemetry', () => ({ trackChatTelemetry: vi.fn() }))
vi.mock('../../../stream/handlers/historyRestoreHelper', () => ({
  restoreRuntimeStateFromHistory: () => ({ agentSteps: [], toolEvents: [], agentMode: null }),
}))
vi.mock('../../utils/evictSessionData', () => ({ evictChatStoreSessionData: vi.fn(() => ({})) }))
vi.mock('../../../messages/messageCache', () => ({
  getCachedMessages: vi.fn(async () => undefined),
  cacheMessages: vi.fn(),
  appendCachedMessages: vi.fn(),
  touchSessionMeta: vi.fn(),
  clearSessionCache: vi.fn(),
}))
vi.mock('../../../messages/actions/titleGenerationDedupe', () => ({ requestTitleGenerationOnce: vi.fn() }))
vi.mock('../../../../useChatSplitStore', () => ({ useChatSplitStore: { getState: () => ({}) } }))
vi.mock('../../../../useSpaceContextTabsStore', () => ({ useSpaceContextTabsStore: { getState: () => ({}) } }))
vi.mock('../../../../useChatRuntimeStore', () => ({
  useChatRuntimeStore: {
    getState: () => ({
      reconcileSubagentRunsFromArchive: vi.fn(),
      evictSession: vi.fn(),
    }),
    setState: vi.fn(),
  },
}))
vi.mock('../../../../useSessionReadStore', () => ({
  useSessionReadStore: { getState: () => ({ markViewed: vi.fn() }) },
}))
vi.mock('@/services/sessionFreshness', () => ({ markSessionFresh: vi.fn(), markSessionStale: vi.fn() }))
vi.mock('@tabtin/smartsheet-ui/toast', () => ({ toast: vi.fn() }))
vi.mock('@/i18n', () => ({ default: { t: (k: string) => k } }))
vi.mock('@/services/agentService/sessionMessages', () => ({
  getSessionMessagesFacade: () => ({
    captureEpoch: () => 0,
    commitServerMerge: (_epoch: number, write: () => void) => {
      write()
      return 'committed'
    },
  }),
}))

// Windows/无本机运行时场景：无 transcript，全量历史只能来自服务端翻页。
vi.mock('@/services/localAgentClient', () => ({ isLocalRuntimeAvailable: () => false }))
vi.mock('@/services/localTranscript', () => ({
  hasLocalTranscript: vi.fn(async () => false),
  readLocalTranscript: vi.fn(),
  enrichWithServerMetadata: vi.fn(() => []),
  forkLocalSessionArchive: vi.fn(),
}))

function makeSession(id: string, spaceId: string): ChatSession {
  return { id, space_id: spaceId, title: `session-${id}`, title_is_default: false } as unknown as ChatSession
}

function makeMessage(id: string): ChatMessage {
  return { id, role: 'user', content: `msg-${id}` } as unknown as ChatMessage
}

describe('跨设备历史补全 preloadFullHistory', () => {
  const SPACE = 'space-1'
  const SESSION = 'session-cross-device'

  type State = {
    sessions: ChatSession[]
    sessionsBySpaceId: Record<string, ChatSession[]>
    currentSessionId: string | null
    currentSessionIdBySpaceId: Record<string, string | null>
    messagesBySessionId: Record<string, ChatMessage[]>
    hasMoreBySessionId: Record<string, boolean>
    isLoadingMoreBySessionId: Record<string, boolean>
    checkpointsBySessionId: Record<string, Record<string, string>>
    lastContextSyncFingerprintBySessionId: Record<string, string>
    isLoading: boolean
  }
  let state: State

  const setSessionMessages = vi.fn((sessionId: string, messages: ChatMessage[]) => {
    state.messagesBySessionId = { ...state.messagesBySessionId, [sessionId]: messages }
  })
  const prependOlderMessages = vi.fn((sessionId: string, older: ChatMessage[]) => {
    const existing = state.messagesBySessionId[sessionId] ?? []
    const ids = new Set(existing.map((m) => m.id))
    const deduped = older.filter((m) => !ids.has(m.id))
    setSessionMessages(sessionId, [...deduped, ...existing])
  })
  const get = () => ({
    ...state,
    setSessionMessages,
    prependOlderMessages,
    applyLoadedMessages: (sid: string, messages: ChatMessage[]) => setSessionMessages(sid, messages),
    hydrateFromCache: (sid: string, messages: ChatMessage[]) => setSessionMessages(sid, messages),
    reconcileFromServer: (sid: string, _fetchEpoch: number, messages: ChatMessage[]) => {
      const existing = state.messagesBySessionId[sid] ?? []
      const ids = new Set(existing.map((m) => m.id))
      setSessionMessages(sid, [...existing, ...messages.filter((m) => !ids.has(m.id))])
      return { changed: true, newCount: messages.length, dropped: false }
    },
    clearSessionMessages: (sid: string) => setSessionMessages(sid, []),
    setCurrentSessionForSpace: vi.fn(),
  }) as unknown as SessionCrudStore
  const set = vi.fn((partial: unknown) => {
    const patch = typeof partial === 'function'
      ? (partial as (s: State) => Partial<State>)(state)
      : partial as Partial<State>
    state = { ...state, ...patch }
  })

  const listMock = vi.fn()
  const makeActions = () => createSessionCrudActions(get as never, set as never, {
    getChatClient: () => ({ messages: { list: listMock } }) as never,
    resolveActiveSpaceId: () => SPACE,
    emptySessions: [],
  })

  /** 按当前最旧 id 游标返回翻页数据：每页 2 条，共 3 页后 has_more=false。 */
  const stubPagedHistory = () => {
    const pages: Record<string, ChatMessage[]> = {
      m50: [makeMessage('m50'), makeMessage('m51')], // 初始页（limit=50）占 m50+
      m40: [makeMessage('m40'), makeMessage('m41')],
      m30: [makeMessage('m30'), makeMessage('m31')],
    }
    listMock.mockImplementation(async (_sid: string, params: { limit?: number; before?: string }) => {
      if (params.limit === 50) {
        return { messages: pages.m50, has_more: true, total: 6 }
      }
      const anchor = params.before ?? ''
      if (anchor === 'm50') return { messages: pages.m40, has_more: true, total: 6 }
      if (anchor === 'm40') return { messages: pages.m30, has_more: false, total: 6 }
      return { messages: [], has_more: false, total: 6 }
    })
    return pages
  }

  /** loadSessionMessages 后台触发补全不阻塞主链，轮询等 hasMore 收敛到 false。 */
  const waitForPreloadSettled = async (timeoutMs = 3000) => {
    const startAt = Date.now()
    while (state.hasMoreBySessionId[SESSION] !== false) {
      if (Date.now() - startAt > timeoutMs) throw new Error('preload not settled in time')
      await new Promise(resolve => setTimeout(resolve, 10))
    }
  }

  beforeEach(() => {
    state = {
      sessions: [makeSession(SESSION, SPACE)],
      sessionsBySpaceId: { [SPACE]: [makeSession(SESSION, SPACE)] },
      currentSessionId: SESSION,
      currentSessionIdBySpaceId: {},
      messagesBySessionId: {},
      hasMoreBySessionId: {},
      isLoadingMoreBySessionId: {},
      checkpointsBySessionId: {},
      lastContextSyncFingerprintBySessionId: {},
      isLoading: false,
    }
    setSessionMessages.mockClear()
    prependOlderMessages.mockClear()
    listMock.mockReset()
    useSessionAccessStore.setState({ bySessionId: {} })
  })

  afterEach(() => {
    useSessionAccessStore.setState({ bySessionId: {} })
  })

  it('hasMore=true 时循环翻页拉到 has_more=false，全量历史入 store', async () => {
    stubPagedHistory()
    state.messagesBySessionId[SESSION] = [makeMessage('m50'), makeMessage('m51')]
    state.hasMoreBySessionId[SESSION] = true

    const actions = makeActions()
    await actions.preloadFullHistory(SESSION)

    const ids = (state.messagesBySessionId[SESSION] ?? []).map((m) => m.id)
    expect(ids).toEqual(['m30', 'm31', 'm40', 'm41', 'm50', 'm51'])
    expect(state.hasMoreBySessionId[SESSION]).toBe(false)
    expect(state.isLoadingMoreBySessionId[SESSION]).toBe(false)
    // 初始已带 2 条 + 两页翻页请求
    expect(listMock).toHaveBeenCalledTimes(2)
  })

  it('hasMore 非 true 时不发起请求', async () => {
    stubPagedHistory()
    state.messagesBySessionId[SESSION] = [makeMessage('m50')]
    state.hasMoreBySessionId[SESSION] = false

    const actions = makeActions()
    await actions.preloadFullHistory(SESSION)
    expect(listMock).not.toHaveBeenCalled()

    delete state.hasMoreBySessionId[SESSION]
    await actions.preloadFullHistory(SESSION)
    expect(listMock).not.toHaveBeenCalled()
  })

  it('同会话并发补全只跑一个循环（in-flight 去重）', async () => {
    stubPagedHistory()
    state.messagesBySessionId[SESSION] = [makeMessage('m50'), makeMessage('m51')]
    state.hasMoreBySessionId[SESSION] = true

    const actions = makeActions()
    const [first, second] = await Promise.all([
      actions.preloadFullHistory(SESSION),
      actions.preloadFullHistory(SESSION),
    ])
    expect(first).toBeUndefined()
    expect(second).toBeUndefined()
    // 只有一个循环在跑：两页翻页请求，不会翻倍
    expect(listMock).toHaveBeenCalledTimes(2)
    expect(state.hasMoreBySessionId[SESSION]).toBe(false)
  })

  it('共享会话（shareId 接入）不补全', async () => {
    stubPagedHistory()
    state.messagesBySessionId[SESSION] = [makeMessage('m50')]
    state.hasMoreBySessionId[SESSION] = true
    useSessionAccessStore.getState().setSharedAccess({ shareId: 'share-x', sessionId: SESSION })

    const actions = makeActions()
    await actions.preloadFullHistory(SESSION)
    expect(listMock).not.toHaveBeenCalled()
  })

  it('连续翻页失败达上限后放弃，不阻塞后续重进会话续跑', async () => {
    listMock.mockRejectedValue(new Error('network down'))
    state.messagesBySessionId[SESSION] = [makeMessage('m50')]
    state.hasMoreBySessionId[SESSION] = true

    const actions = makeActions()
    await actions.preloadFullHistory(SESSION)

    // MAX_STALL=5：5 次失败后放弃（无进展重试计入 stall）
    expect(listMock.mock.calls.filter((c) => c[1]?.limit === 30).length).toBe(5)
    // hasMore 保持 true（失败不清翻页标记），下次进入会话可续跑
    expect(state.hasMoreBySessionId[SESSION]).toBe(true)
  }, 15000)

  it('loadSessionMessages 服务端路径 has_more=true 时自动触发补全', async () => {
    stubPagedHistory()
    // 无内存缓存、无 IDB、无 transcript → 服务端初始页

    const actions = makeActions()
    await actions.loadSessionMessages(SESSION)
    await waitForPreloadSettled()

    // 初始页 + 两页后台补全
    expect(listMock).toHaveBeenCalledTimes(3)
    const ids = (state.messagesBySessionId[SESSION] ?? []).map((m) => m.id)
    expect(ids).toEqual(['m30', 'm31', 'm40', 'm41', 'm50', 'm51'])
    expect(state.hasMoreBySessionId[SESSION]).toBe(false)
  })

  it('loadSessionMessages 内存命中且 hasMore=true 时续跑补全', async () => {
    stubPagedHistory()
    state.messagesBySessionId[SESSION] = [makeMessage('m50'), makeMessage('m51')]
    state.hasMoreBySessionId[SESSION] = true

    const actions = makeActions()
    await actions.loadSessionMessages(SESSION)
    await waitForPreloadSettled()

    // 内存命中不走初始页，只续跑两页翻页
    expect(listMock).toHaveBeenCalledTimes(2)
    const ids = (state.messagesBySessionId[SESSION] ?? []).map((m) => m.id)
    expect(ids).toEqual(['m30', 'm31', 'm40', 'm41', 'm50', 'm51'])
    expect(state.hasMoreBySessionId[SESSION]).toBe(false)
  })
})
