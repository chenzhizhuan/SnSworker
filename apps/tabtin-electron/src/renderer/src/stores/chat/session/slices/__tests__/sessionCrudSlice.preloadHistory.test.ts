/**
 * 跨设备历史补全（preloadFullHistory / runHistoryPreload）回归。
 *
 * 锁定：
 * - 首屏锚定「最新页」：listInitialMessages 探测 → total-offset 拉最新 50 条
 *   （服务端 offset 分页为 ASC 正序，直接 limit 拉到的是会话最旧一页）；
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

/** 80 条消息（m1..m80，ASC 正序），服务端按 offset/before 语义分页。 */
const MESSAGES_80 = Array.from({ length: 80 }, (_, i) => makeMessage(`m${i + 1}`))

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

  /**
   * 80 条真实场景：
   * - limit=50（探测）：ASC 最旧 50 条（m1-m50）+ has_more=true, total=80
   * - limit=50 & offset=30：最新 50 条（m31-m80）
   * - limit=30 & before=m31：m31 之前 30 条（m1-m30），has_more=false（拉全）
   */
  const stubPagedHistory = () => {
    listMock.mockImplementation(async (
      _sid: string,
      params: { limit?: number; offset?: number; before?: string },
    ) => {
      if (params.limit === 50) {
        if (params.offset === 30) {
          return { messages: MESSAGES_80.slice(30), has_more: true, total: 80 }
        }
        return { messages: MESSAGES_80.slice(0, 50), has_more: true, total: 80 }
      }
      if (params.limit === 30 && params.before === 'm31') {
        return { messages: MESSAGES_80.slice(0, 30), has_more: false, total: 80 }
      }
      return { messages: [], has_more: false, total: 80 }
    })
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
    // 首屏已锚定最新页（m31-m80），仍有更早历史
    state.messagesBySessionId[SESSION] = [...MESSAGES_80.slice(30)]
    state.hasMoreBySessionId[SESSION] = true

    const actions = makeActions()
    await actions.preloadFullHistory(SESSION)

    const ids = (state.messagesBySessionId[SESSION] ?? []).map((m) => m.id)
    expect(ids).toEqual(MESSAGES_80.map((m) => m.id))
    expect(state.hasMoreBySessionId[SESSION]).toBe(false)
    expect(state.isLoadingMoreBySessionId[SESSION]).toBe(false)
    // 缺口 30 条，单页翻完：1 次 before 请求
    expect(listMock).toHaveBeenCalledTimes(1)
    expect(listMock).toHaveBeenCalledWith(
      SESSION,
      expect.objectContaining({ limit: 30, before: 'm31' }),
    )
  })

  it('hasMore 非 true 时不发起请求', async () => {
    stubPagedHistory()
    state.messagesBySessionId[SESSION] = [makeMessage('m31')]
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
    state.messagesBySessionId[SESSION] = [...MESSAGES_80.slice(30)]
    state.hasMoreBySessionId[SESSION] = true

    const actions = makeActions()
    await Promise.all([
      actions.preloadFullHistory(SESSION),
      actions.preloadFullHistory(SESSION),
    ])
    // 只有一个循环在跑：1 次翻页请求，不会翻倍
    expect(listMock).toHaveBeenCalledTimes(1)
    expect(state.hasMoreBySessionId[SESSION]).toBe(false)
  })

  it('共享会话（shareId 接入）不补全', async () => {
    stubPagedHistory()
    state.messagesBySessionId[SESSION] = [makeMessage('m31')]
    state.hasMoreBySessionId[SESSION] = true
    useSessionAccessStore.getState().setSharedAccess({ shareId: 'share-x', sessionId: SESSION })

    const actions = makeActions()
    await actions.preloadFullHistory(SESSION)
    expect(listMock).not.toHaveBeenCalled()
  })

  it('连续翻页失败达上限后放弃，不阻塞后续重进会话续跑', async () => {
    listMock.mockRejectedValue(new Error('network down'))
    state.messagesBySessionId[SESSION] = [makeMessage('m31')]
    state.hasMoreBySessionId[SESSION] = true

    const actions = makeActions()
    await actions.preloadFullHistory(SESSION)

    // MAX_STALL=5：5 次失败后放弃（无进展重试计入 stall）
    expect(listMock.mock.calls.filter((c) => c[1]?.limit === 30).length).toBe(5)
    // hasMore 保持 true（失败不清翻页标记），下次进入会话可续跑
    expect(state.hasMoreBySessionId[SESSION]).toBe(true)
  }, 15000)

  it('loadSessionMessages 服务端路径：首屏锚定最新页并自动补全到全量', async () => {
    stubPagedHistory()
    // 无内存缓存、无 IDB、无 transcript → 服务端路径

    const actions = makeActions()
    await actions.loadSessionMessages(SESSION)
    await waitForPreloadSettled()

    // 探测（limit=50）→ 最新页（limit=50&offset=30）→ 补全（limit=30&before=m31）
    expect(listMock).toHaveBeenCalledTimes(3)
    expect(listMock).toHaveBeenNthCalledWith(
      1,
      SESSION,
      expect.objectContaining({ limit: 50 }),
      undefined,
    )
    expect(listMock).toHaveBeenNthCalledWith(
      2,
      SESSION,
      expect.objectContaining({ limit: 50, offset: 30 }),
      undefined,
    )
    expect(listMock).toHaveBeenNthCalledWith(
      3,
      SESSION,
      expect.objectContaining({ limit: 30, before: 'm31' }),
    )
    // 首屏是最新页（m31-m80）而非会话最旧一页；补全后全量
    const ids = (state.messagesBySessionId[SESSION] ?? []).map((m) => m.id)
    expect(ids).toEqual(MESSAGES_80.map((m) => m.id))
    expect(state.hasMoreBySessionId[SESSION]).toBe(false)
  })

  it('loadSessionMessages 内存命中且 hasMore=true 时续跑补全', async () => {
    stubPagedHistory()
    state.messagesBySessionId[SESSION] = [...MESSAGES_80.slice(30)]
    state.hasMoreBySessionId[SESSION] = true

    const actions = makeActions()
    await actions.loadSessionMessages(SESSION)
    await waitForPreloadSettled()

    // 内存命中不走服务端初始页，只续跑 1 次翻页
    expect(listMock).toHaveBeenCalledTimes(1)
    const ids = (state.messagesBySessionId[SESSION] ?? []).map((m) => m.id)
    expect(ids).toEqual(MESSAGES_80.map((m) => m.id))
    expect(state.hasMoreBySessionId[SESSION]).toBe(false)
  })
})
