import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'

import { TeamSpaceMembersSection } from './TeamSpaceMembersSection'

const listSpaceMemberships = vi.fn()
const getMembers = vi.fn()
const listProjectPendingInvitations = vi.fn()
const inviteMember = vi.fn()

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, options?: { defaultValue?: string }) => options?.defaultValue ?? _key,
  }),
}))

vi.mock('@stores/useSpaceStore', () => ({
  useSpaceStore: (selector: (state: { loadSpaces: () => Promise<void> }) => unknown) =>
    selector({ loadSpaces: vi.fn() }),
}))

vi.mock('@stores/useAuthStore', () => ({
  useAuthStore: (selector: (state: { user: { id: string } }) => unknown) =>
    selector({ user: { id: 'owner-1' } }),
}))

vi.mock('@/hooks/useTeamSpacePresence', () => ({
  useTeamSpacePresence: () => ({ isUserOnline: () => false }),
}))

vi.mock('@/services/spaceAccessApi', () => ({
  SpaceAccessApiService: {
    listSpaceMemberships: (...args: unknown[]) => listSpaceMemberships(...args),
  },
}))

vi.mock('@/services/memberApi', () => ({
  MemberApiService: {
    getMembers: (...args: unknown[]) => getMembers(...args),
  },
}))

vi.mock('@/services/projectApi', () => ({
  ProjectApiService: {
    listProjectPendingInvitations: (...args: unknown[]) => listProjectPendingInvitations(...args),
    inviteMember: (...args: unknown[]) => inviteMember(...args),
  },
}))

vi.mock('@components/ui', () => ({
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type="button" {...props}>{children}</button>
  ),
  ScrollArea: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  toast: vi.fn(),
}))

describe('TeamSpaceMembersSection ', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listSpaceMemberships.mockResolvedValue({
      memberships: [
        {
          id: 'm-owner',
          space_id: 'project-1',
          user_id: 'owner-1',
          role: 'owner',
          permissions: {},
          is_active: true,
          joined_at: '2026-07-21T00:00:00Z',
          updated_at: '2026-07-21T00:00:00Z',
        },
      ],
      total: 1,
    })
    getMembers.mockResolvedValue({
      members: [
        {
          user_id: 'owner-1',
          user: { nickname: '师傅', username: 'master', email: 'a@t.com' },
        },
        {
          user_id: 'invitee-1',
          user: { nickname: '徒弟', username: 'apprentice', email: 'b@t.com' },
        },
      ],
    })
    listProjectPendingInvitations.mockResolvedValue([
      {
        membership_id: 'pending-1',
        user_id: 'invitee-1',
        user_name: '徒弟',
        role: 'editor',
        invited_at: '2026-07-21T01:00:00Z',
      },
    ])
  })

  it('展示待接受状态，并把已邀请成员移出可邀请列表', async () => {
    render(
      <TeamSpaceMembersSection
        space={{
          id: 'project-1',
          name: '上山',
          organization_id: 'org-1',
          type: 'team_space',
        } as never}
        scrollable={false}
        showHeader={false}
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('project-pending-invitation')).not.toBeNull()
    })
    expect(screen.getByText('徒弟')).not.toBeNull()
    expect(screen.getAllByText('待接受').length).toBeGreaterThan(0)

    // 新交互（MemberSearchSelect）：初始候选不含已在项目/待接受的成员 → 空态提示。
    const combobox = screen.getByRole('combobox')
    fireEvent.click(combobox)
    const listbox = await screen.findByRole('listbox')
    expect(within(listbox).getByText('暂无可选成员')).not.toBeNull()

    // 搜索后两类成员都出现，但分别以「已在项目」「待接受」灰显且禁选。
    fireEvent.change(combobox, { target: { value: '徒弟' } })
    await waitFor(() => {
      expect(within(listbox).getAllByRole('option').length).toBe(2)
    })
    const options = within(listbox).getAllByRole('option') as HTMLButtonElement[]
    expect(options[0]?.textContent).toContain('已在项目')
    expect(options[1]?.textContent).toContain('待接受')
    expect(options.every(option => option.disabled)).toBe(true)
  })
})
