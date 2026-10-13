/**
 * upsertWorkspace 回归：问一句（AskPage ensureAsk）lazy provision 的现场
 * 必须立即出现在 spaces 列表。
 *
 * 背景（2026-10-13 用户报告）：首次进入问一句时 ensureAsk 才真正创建
 * system_ask 现场，而 loadSpaces 早已跑完 —— store 快照里没有该行。
 * 发送链路 provisionNewSession 的 resolveChatScopeHost 只查
 * useSpaceStore.spaces，找不到 → 抛「创建会话前必须加载目标 Space」→
 * 用户看到「创建会话失败，请重试发送」。
 *
 * 修复：AskPage 在 ensureAsk 成功后调用 upsertWorkspace（幂等）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@tabtin/shared', () => ({
  withPersistSafety: (options: unknown) => options,
}))

vi.mock('@tabtin/config', () => ({
  API_ENDPOINTS: {},
  joinApiPath: (...parts: string[]) => parts.filter(Boolean).join('/'),
}))

const mockListProjects = vi.fn()
const mockListWorkspaces = vi.fn()

vi.mock('../services/space-api.js', () => ({
  SpaceApiService: {},
  ProjectApiService: {
    list: (...args: unknown[]) => mockListProjects(...args),
  },
  WorkspaceApiService: {
    list: (...args: unknown[]) => mockListWorkspaces(...args),
  },
  AgentApiService: {},
  ApprovalMemoApiService: {},
}))

vi.mock('../runtime.js', () => ({
  getRuntime: () => ({
    bridge: {
      onSpaceDeleted: vi.fn(),
      resolveCrawlspaceId: vi.fn(() => null),
      setActiveSpace: vi.fn(),
      getCurrentDeviceId: () => null,
    },
  }),
}))

vi.mock('./view-navigation.js', () => ({
  onNavigate: vi.fn(),
  emitNavigate: vi.fn(),
}))

vi.mock('./session-reset-registry.js', () => ({
  registerResetAction: vi.fn(),
}))

vi.mock('./use-organization-store.js', () => ({
  useOrganizationStore: {
    getState: () => ({ selectedOrganization: null }),
    subscribe: vi.fn(() => () => {}),
  },
}))

let useSpaceStore: typeof import('./use-space-store.js').useSpaceStore

const ASK_WORKSPACE = {
  id: 'ask-ws-1',
  organization_id: 'org-1',
  name: '问一句工作空间',
  working_dir: '/Users/me/SnSworker/org/ask',
  working_dir_type: 'mixed',
  device_id: 'device-1',
  device_online: true,
  provisioning_source: 'system_ask',
  is_companion: true,
} as never

describe('useSpaceStore.upsertWorkspace — lazy provision 现场立即可见', () => {
  beforeEach(async () => {
    vi.resetModules()
    mockListProjects.mockReset().mockResolvedValue({ spaces: [], total: 0 })
    mockListWorkspaces.mockReset().mockResolvedValue([])
    window.localStorage.clear()

    const mod = await import('./use-space-store.js')
    useSpaceStore = mod.useSpaceStore
    useSpaceStore.setState({
      spaces: [],
      selectedSpace: null,
      agentCache: {},
      selectedAgent: null,
      isLoading: false,
      isCreating: false,
      error: null,
      loadRetryCount: 0,
      lastLoadError: null,
    })
  })

  it('store 无该行时追加（workspace 形状，带 provisioning_source）', () => {
    useSpaceStore.getState().upsertWorkspace(ASK_WORKSPACE, 'org-1')

    const spaces = useSpaceStore.getState().spaces
    expect(spaces).toHaveLength(1)
    expect(spaces[0]?.id).toBe('ask-ws-1')
    expect(spaces[0]?.type).toBe('workspace')
    expect(spaces[0]?.organization_id).toBe('org-1')
    expect(spaces[0]?.provisioning_source).toBe('system_ask')
  })

  it('store 已有该行时幂等更新（不重复追加）', () => {
    useSpaceStore.getState().upsertWorkspace(ASK_WORKSPACE, 'org-1')
    useSpaceStore.getState().upsertWorkspace(
      { ...ASK_WORKSPACE, name: '问一句工作空间2' } as never,
      'org-1',
    )

    const spaces = useSpaceStore.getState().spaces
    expect(spaces).toHaveLength(1)
    expect(spaces[0]?.name).toBe('问一句工作空间2')
  })

  it('upsert 后 resolveChatScopeHost 依赖的 store 查找能命中（发送链路不再抛错）', () => {
    useSpaceStore.getState().upsertWorkspace(ASK_WORKSPACE, 'org-1')

    const state = useSpaceStore.getState()
    const found = state.spaces.find((s) => s.id === 'ask-ws-1')
    expect(found).toBeDefined()
    expect(found?.type).not.toBe('team_space')
  })
})
