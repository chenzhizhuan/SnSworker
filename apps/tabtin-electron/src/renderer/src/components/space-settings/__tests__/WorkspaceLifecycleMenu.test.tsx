import React from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

const canManageSpaceLifecycleMock = vi.hoisted(() => vi.fn(() => true))
const useSpaceDeleteGuardMock = vi.hoisted(() =>
  vi.fn(() => ({
    canDelete: true,
    isResolving: false,
    isRemoteViewer: false,
    blockReason: null,
    controlDeviceName: null,
  })),
)
const projectApiTrashMock = vi.hoisted(() => vi.fn(async () => undefined))
const toastMock = vi.hoisted(() => vi.fn())

vi.mock('@/hooks/useCanManageSpaceLifecycle', () => ({
  canManageSpaceLifecycle: canManageSpaceLifecycleMock,
}))

vi.mock('../hooks/useSpaceDeleteGuard', () => ({
  useSpaceDeleteGuard: useSpaceDeleteGuardMock,
}))

vi.mock('@stores/useSpaceStore', () => ({
  useSpaceStore: Object.assign(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({
        selectedAgent: null,
        deleteSpace: vi.fn(),
        archiveSpace: vi.fn(),
        loadSpaces: vi.fn(),
        isLoading: false,
        error: null,
      }),
    {
      getState: () => ({ error: null }),
    },
  ),
}))

vi.mock('@stores/useOrganizationStore', () => ({
  useOrganizationStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      currentUserRole: 'editor',
      selectedOrganization: { id: 'org-1', owner_id: 'user-1' },
    }),
}))

vi.mock('@stores/useAuthStore', () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ user: { id: 'user-1' } }),
}))

vi.mock('@components/settings/SettingsNameConfirmDialog', () => ({
  SettingsNameConfirmDialog: () => null,
}))

vi.mock('@components/context-space/dirtyExitConfirm/spaceDeleteGuard', () => ({
  confirmDirtyBeforeSpaceDelete: vi.fn(async () => true),
}))

vi.mock('@/utils/featureFlags', () => ({
  SPACE_TRASH_UI_ENABLED: true,
  SPACE_ARCHIVE_UI_ENABLED: false,
}))

vi.mock('@tabtin/app-shell', () => ({
  ProjectApiService: { trash: projectApiTrashMock },
  // 组件同时从 @tabtin/app-shell 导入 cn（SpaceSettingsPane 同款工具）
  cn: (...classes: Array<string | false | null | undefined>) =>
    classes.filter(Boolean).join(' '),
}))

vi.mock('@tabtin/smartsheet-ui', () => ({
  Button: ({ children, ...props }: Record<string, unknown>) => {
    const React = require('react') as typeof import('react')
    return React.createElement(
      'button',
      { ...props, type: 'button' },
      children as never,
    )
  },
  ConfirmDialog: ({
    open,
    onConfirm,
  }: {
    open: boolean
    onConfirm?: () => void
  }) => {
    const React = require('react') as typeof import('react')
    if (!open) return null
    return React.createElement(
      'button',
      { type: 'button', 'data-testid': 'confirm-dialog-confirm', onClick: onConfirm },
      'confirm',
    )
  },
  toast: toastMock,
}))

import { WorkspaceLifecycleMenu } from '../WorkspaceLifecycleMenu'
import type { Space } from '@tabtin/app-shell'

const space = {
  id: 'ws-1',
  name: 'workspace-abc123',
  organization_id: 'org-1',
  type: 'workspace',
  workspace_record: true,
  status: 'active',
  table_count: 0,
  order: 0,
  is_archived: false,
  is_default: false,
  created_at: '',
  updated_at: '',
} as Space

describe('WorkspaceLifecycleMenu', () => {
  beforeEach(() => {
    projectApiTrashMock.mockClear()
    toastMock.mockClear()
    canManageSpaceLifecycleMock.mockReturnValue(true)
    useSpaceDeleteGuardMock.mockReturnValue({
      canDelete: true,
      isResolving: false,
      isRemoteViewer: false,
      blockReason: null,
      controlDeviceName: null,
    })
  })

  it('有权限时渲染页底危险操作区与删除按钮', () => {
    render(<WorkspaceLifecycleMenu space={space} />)
    expect(screen.getByTestId('workspace-lifecycle-danger')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'actions.delete' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'actions.workspaceMenuLabel' })).toBeNull()
  })

  it('无权限时不渲染菜单', () => {
    canManageSpaceLifecycleMock.mockReturnValue(false)
    const { container } = render(<WorkspaceLifecycleMenu space={space} />)
    expect(container.childElementCount).toBe(0)
  })

  it('workspace 类型不显示回收站入口（物理删除语义，避免 30 天可恢复误导）', () => {
    render(<WorkspaceLifecycleMenu space={space} />)
    expect(screen.queryByRole('button', { name: 'actions.trash' })).toBeNull()
  })

  it('team_space 类型显示回收站入口且走 ProjectApiService.trash', async () => {
    const teamSpace = {
      ...space,
      type: 'team_space',
      workspace_record: false,
    } as typeof space
    const user = userEvent.setup()
    render(<WorkspaceLifecycleMenu space={teamSpace} />)
    const trashButton = screen.getByRole('button', { name: 'actions.trash' })
    expect(trashButton).toBeTruthy()
    await user.click(trashButton)
    const confirmButton = await screen.findByRole('button', { name: 'confirm' })
    await user.click(confirmButton)
    await vi.waitFor(() => {
      expect(projectApiTrashMock).toHaveBeenCalledWith(teamSpace.id)
      expect(projectApiTrashMock).toHaveBeenCalledTimes(1)
    })
  })
})
