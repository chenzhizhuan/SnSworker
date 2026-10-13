/**
 * 问一句（askOnlyAgent）首发会话创建回归。
 *
 * 用户报告（2026-10-13）：问一句页不点「新问答」、直接在输入框发送，
 * 弹「创建会话失败，请重试发送」。服务器侧证据：无任何 agent_mode='ask'
 * 的会话创建请求到达后端（POST /sessions 与 /sessions/quick-start 均无），
 * 说明失败发生在前端 ensure 链路的 HTTP 之前。
 *
 * 本文件按真实 store 形态复现：ask 专属工作空间在 spaces 里（type='workspace'，
 * 后端 list_workspaces 不排除 system_ask），无历史 ask 会话，走
 * ensureSessionForSpace(preferQuickStart, agentMode='ask')。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ChatSession } from '@tabtin/chat-client'
import {
  createSessionLifecycleAction,
  _resetSessionProvisionLatchesForTests,
  type SessionLifecycleStore,
} from '../sessionLifecycleAction'

vi.mock('../../sessionPrefetchAction', () => ({
  createSessionPrefetchAction: vi.fn(() => ({ prefetchDraftSession: vi.fn() })),
}))

vi.mock('../../../../useChatModelStore', () => ({
  useChatModelStore: {
    getState: () => ({
      availableModels: [{ id: 'model-1' }],
      userDefaultModelId: 'model-1',
      switchModel: vi.fn().mockResolvedValue(undefined),
    }),
  },
}))

vi.mock('@/utils/chatModelGuards', () => ({
  filterSendableChatModels: (models: unknown[]) => models,
}))

vi.mock('@/services/sessionCodeRootBinding', () => ({
  rehomeSessionCodeRoot: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('@components/onboarding/external-import/externalOpenedSessionRegistry', () => ({
  getExternalOpenedSessionIds: vi.fn(() => new Set<string>()),
}))

vi.mock('../../../execution/chatTelemetry', () => ({
  trackChatTelemetry: vi.fn(),
}))

vi.mock('@/services/rehomeConversationScopeLayout', () => ({
  rehomeConversationScopeLayout: vi.fn(),
  rehomeConversationScopeLayoutAfterProvision: vi.fn(),
}))

vi.mock('../../../execution/sendTimingTrace', () => ({
  getActiveSendTimingTrace: vi.fn(() => null),
  buildSendTimingPayload: vi.fn(() => ({})),
}))

vi.mock('../../../execution/modelPreference', () => ({
  readRuntimeModelPreference: vi.fn(() => null),
}))

vi.mock('@/services/loadOrganizationDeviceModelPreferences', () => ({
  loadOrganizationDeviceModelPreferences: vi.fn().mockResolvedValue({}),
  readCachedOrganizationDeviceModelPreferences: vi.fn(() => ({})),
}))

vi.mock('../../../shared/resolveRuntimeModelSelection', () => ({
  resolveRuntimeDefaultModelId: vi.fn(({ preferredModelId }: { preferredModelId?: string }) => preferredModelId ?? null),
  toProvisionModelId: vi.fn((id: string | null) => id ?? undefined),
  createRuntimeModelAvailabilityChecker: vi.fn(() => (id: string) => Boolean(id)),
}))

const mockSelectAgent = vi.fn()
const spaceStoreState = {
  selectedAgent: {
    id: 'agent-1',
    organization_id: 'org-1',
    is_active: true,
  } as { id: string; organization_id: string; is_active: boolean } | null,
  selectedSpace: null as { id: string; type?: string; organization_id: string } | null,
  spaces: [] as Array<{ id: string; type?: string; organization_id: string; project_id?: string | null }>,
  selectAgent: mockSelectAgent,
}
const mockListAgents = vi.fn()

vi.mock('@stores/useSpaceStore', () => ({
  useSpaceStore: {
    getState: () => spaceStoreState,
  },
}))

vi.mock('@tabtin/app-shell', () => {
  const base = {
    AgentApiService: {
      listAgents: (...args: unknown[]) => mockListAgents(...args),
    },
    registerResetAction: vi.fn(),
    ZIndex: new Proxy({}, { get: () => 1000 }),
    onNavigate: vi.fn(),
    offNavigate: vi.fn(),
    onOrganizationSelected: vi.fn(),
    offOrganizationSelected: vi.fn(),
  }
  return new Proxy(base, {
    get: (target, prop) => {
      if (prop === 'then') return undefined
      if (prop in target) return target[prop as keyof typeof target]
      return vi.fn()
    },
  })
})

describe('问一句首发：ensureSessionForSpace(agentMode=ask)', () => {
  const ASK_SPACE = 'ask-workspace-1'
  let state: SessionLifecycleStore
  const createMock = vi.fn()
  const quickStartMock = vi.fn()

  const get = () => state
  const set = vi.fn((partial: unknown) => {
    const patch = typeof partial === 'function'
      ? (partial as (s: SessionLifecycleStore) => Partial<SessionLifecycleStore>)(state)
      : (partial as Partial<SessionLifecycleStore>)
    state = { ...state, ...patch }
  })

  const makeActions = () =>
    createSessionLifecycleAction(get, set as never, {
      getChatClient: () => ({
        sessions: { create: createMock, quickStart: quickStartMock },
      }) as never,
      resolveActiveSpaceId: () => ASK_SPACE,
      emptySessions: [],
    })

  beforeEach(() => {
    _resetSessionProvisionLatchesForTests()
    spaceStoreState.selectedAgent = { id: 'agent-1', organization_id: 'org-1', is_active: true }
    spaceStoreState.selectedSpace = null
    // 后端 list_workspaces 不排除 system_ask：ask 专属工作空间在 spaces 列表里。
    spaceStoreState.spaces = [
      { id: ASK_SPACE, type: 'workspace', organization_id: 'org-1' },
      { id: 'workspace-x', type: 'workspace', organization_id: 'org-1' },
    ]
    state = {
      currentSessionId: null,
      draftSessionBySpaceId: {},
      messagesBySessionId: {},
      sessions: [],
      sessionsBySpaceId: { [ASK_SPACE]: [] },
      currentSessionIdBySpaceId: { [ASK_SPACE]: null },
      checkpointsBySessionId: {},
      lastContextSyncFingerprintBySessionId: {},
    }
    createMock.mockReset()
    quickStartMock.mockReset()
    mockListAgents.mockReset()
    createMock.mockImplementation(async (): Promise<ChatSession> =>
      ({ id: 'sess-ask-1', space_id: ASK_SPACE, agent_mode: 'ask' }) as unknown as ChatSession)
    quickStartMock.mockImplementation(async () => ({
      session: { id: 'sess-ask-1', space_id: ASK_SPACE, agent_mode: 'ask' },
      context_fingerprint: 'fp-1',
    }))
  })

  it('首发 ensure（preferQuickStart + agentMode=ask）能创建出 ask 会话', async () => {
    const actions = makeActions()
    const result = await actions.ensureSessionForSpace(
      ASK_SPACE,
      'org-1',
      'model-1',
      { trigger: 'pre_send', preferQuickStart: true, agentMode: 'ask' },
    )

    expect(result.sessionId).toBe('sess-ask-1')
    expect(quickStartMock).toHaveBeenCalledTimes(1)
    const binding = quickStartMock.mock.calls[0]?.[4] as { agentMode?: string }
    expect(binding?.agentMode).toBe('ask')
  })

  it('spaces 中没有 ask 工作空间时抛「创建会话前必须加载目标 Space」', async () => {
    spaceStoreState.spaces = [{ id: 'workspace-x', type: 'workspace', organization_id: 'org-1' }]
    const actions = makeActions()

    await expect(
      actions.ensureSessionForSpace(
        ASK_SPACE,
        'org-1',
        'model-1',
        { trigger: 'pre_send', preferQuickStart: true, agentMode: 'ask' },
      ),
    ).rejects.toThrow('创建会话前必须加载目标 Space')
  })
})
