/**
 * 本机 runtime 发送物料测试：Project 编排上下文保活（TODO #4）。
 *
 * 回归背景：chat 视觉 Focus 的 syncContext（chatPanelController.requestContextSync，
 * P1-7）会把 appMeta 置 null，覆盖编排打开时写入的 { project_id }。用户在编排
 * 对话里的下一条消息若不带 project_id，主进程会以「无 Project 上下文」重建
 * runtime，静默摘除 project_members_list / project_tasks_create —— 表现为
 * 「AI 编排确认方案后不写看板」。发送物料需按会话宿主 Project 兜底补回
 * project_id；会话归属的 Project 是创建期绑定，视觉 Focus 不改变它。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getLastAppContextMock, spaceStoreStateMock } = vi.hoisted(() => ({
  getLastAppContextMock: vi.fn(() => null as unknown),
  spaceStoreStateMock: {
    spaces: [
      { id: 'team-space-1', type: 'team_space', organization_id: 'org-1' },
      { id: 'workspace-1', type: 'workspace', project_id: 'team-space-1' },
      { id: 'workspace-personal', type: 'workspace', organization_id: 'org-1' },
    ],
    selectedSpace: null,
  },
}))

vi.mock('@tabtin/app-shell', () => ({
  getCapabilityOverride: () => undefined,
}))

vi.mock('@stores/useMemoRecordStyleStore', () => ({
  useMemoRecordStyleStore: {
    getState: () => ({ isEnabled: () => false }),
  },
}))

vi.mock('@stores/useOrganizationStore', () => ({
  useOrganizationStore: {
    getState: () => ({ selectedOrganization: null }),
  },
}))

vi.mock('@stores/useSpaceStore', () => ({
  useSpaceStore: {
    getState: () => spaceStoreStateMock,
  },
}))

vi.mock('../../../session/slices/contextSyncSlice', () => ({
  getLastAppContext: (...args: unknown[]) => getLastAppContextMock(...args),
}))

vi.mock('../../actions/buildUserVisibleBlocks', () => ({
  buildUserVisibleBlocks: (text: string) => [{ type: 'text', text }],
}))

import { buildLocalRuntimeSendPayload } from '../buildLocalRuntimeSendPayload'
import type { BuildLocalRuntimeSendPayloadInput } from '../buildLocalRuntimeSendPayload'

function buildInput(
  overrides: Partial<BuildLocalRuntimeSendPayloadInput> = {},
): BuildLocalRuntimeSendPayloadInput {
  return {
    sessionId: 'session-1',
    message: '你不是应该给我编排任务吗',
    displayMessage: '你不是应该给我编排任务吗',
    modelId: 'model-1',
    currentModel: null,
    currentAgent: null,
    currentAgentMode: 'agent',
    currentApprovalMode: 'always_ask',
    isGroupSpace: false,
    clientMessageId: 'client-1',
    capturedSpaceId: 'team-space-1',
    capturedRuntimeSpaceId: 'workspace-1',
    capturedEnabledApps: [],
    spaces: [],
    streamDeps: {
      client: {} as never,
      addStreamingSession: vi.fn(),
      removeStreamingSession: vi.fn(),
      updateSessionTokenUsageInCaches: vi.fn(),
      updateSessionInCaches: vi.fn(),
    },
    ...overrides,
  }
}

describe('buildLocalRuntimeSendPayload — Project 编排上下文保活', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getLastAppContextMock.mockReturnValue(null)
  })

  it('TODO#4 回归：chat 视觉 Focus 清空 appMeta 后，Project 宿主发送补回 project_id', () => {
    // 编排会话打开时 syncContext('project_tasks', {project_id})；随后用户聚焦
    // 聊天面板，requestContextSync 以 appType='chat'、appMeta=null 覆盖缓存。
    getLastAppContextMock.mockReturnValue({
      appType: 'chat',
      appMeta: null,
      openTabs: [],
      spaceId: 'team-space-1',
    })

    const { options } = buildLocalRuntimeSendPayload(buildInput())
    const appContext = options.appContext as { appMeta?: Record<string, unknown> | null }

    expect(appContext?.appMeta?.project_id).toBe('team-space-1')
  })

  it('appMeta 已带 project_id 时原样保留，不重复注入', () => {
    const cachedAppMeta = {
      project_id: 'team-space-1',
      orchestration_scope: 'project_tasks',
    }
    getLastAppContextMock.mockReturnValue({
      appType: 'project_tasks',
      appMeta: cachedAppMeta,
      openTabs: [],
      spaceId: 'team-space-1',
    })

    const { options } = buildLocalRuntimeSendPayload(buildInput())
    const appContext = options.appContext as { appMeta?: Record<string, unknown> | null }

    expect(appContext?.appMeta).toBe(cachedAppMeta)
  })

  it('非 Project 宿主（个人 workspace 会话）不注入 project_id', () => {
    getLastAppContextMock.mockReturnValue({
      appType: 'chat',
      appMeta: null,
      openTabs: [],
      spaceId: 'workspace-personal',
    })

    const { options } = buildLocalRuntimeSendPayload(buildInput({
      capturedSpaceId: 'workspace-personal',
      capturedRuntimeSpaceId: 'workspace-personal',
    }))
    const appContext = options.appContext as { appMeta?: Record<string, unknown> | null }

    expect(appContext?.appMeta).toBeNull()
  })

  it('app 重启后缓存为空：Project 宿主首轮发送也能带上 project_id', () => {
    getLastAppContextMock.mockReturnValue(null)

    const { options } = buildLocalRuntimeSendPayload(buildInput())
    const appContext = options.appContext as {
      appMeta?: Record<string, unknown> | null
      projectSpaceId?: string
    }

    expect(appContext?.appMeta?.project_id).toBe('team-space-1')
    // 既有 projectSpaceId 投影语义保留。
    expect(appContext?.projectSpaceId).toBe('team-space-1')
  })
})
