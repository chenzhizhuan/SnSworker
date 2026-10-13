/**
 * MemberSearchSelect — 组织成员可搜索选择器。
 *
 * 背景（2026-10-13 TODO 清单 #1/#3）：组织成员可达数百人（当前部署 751 人），
 * 旧实现 `getMembers({ limit: 200 })` + 原生 <select> 有两个问题：
 *   1. 超过 200 人的部分在下拉里永远不可见（即使已是 Project 成员）；
 *   2. 数百人的纯下拉无法定位目标成员。
 *
 * 方案：输入关键字 → 防抖调后端 `search` 参数（匹配用户名/昵称/邮箱，
 * 见 membership.list_organization_members）→ 下拉展示前 50 条实时结果。
 * 未输入时展示调用方提供的 initialOptions（通常为 Project 活跃成员）。
 *
 * 两个消费方：
 *   - TeamSpaceMembersSection（邀请 Organization 成员）
 *   - ProjectTasksPane（新建任务指派人 / 改派）
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2, Search, UserRound } from 'lucide-react'
import { MemberApiService } from '@/services/memberApi'
import type { OrganizationMember } from '@tabtin/app-shell'
import { cn } from '@utils/cn'

export function memberDisplayName(member: OrganizationMember): string {
  return (
    member.user?.nickname ||
    member.user?.username ||
    member.user?.email ||
    member.user_id
  )
}

export interface MemberSearchSelectProps {
  organizationId: string
  /** 当前选中 user_id（空 = 未选）。 */
  value: string
  onChange: (userId: string) => void
  /** 未搜索时展示的候选（如 Project 活跃成员）。 */
  initialOptions: OrganizationMember[]
  /** 不可选的 user_id → 灰显原因文案（如「已在项目」「待接受」）。 */
  disabledOptions?: Record<string, string>
  /** 生效成员集合：候选/搜索结果中的非成员将灰显「未加入项目」（不受组织成员前 N 条截断影响）。 */
  projectActiveUserIds?: Set<string>
  disabled?: boolean
  placeholder?: string
  ariaLabel?: string
  className?: string
  /** 空态提示。 */
  emptyHint?: string
}

interface SearchState {
  keyword: string
  results: OrganizationMember[]
  loading: boolean
  opened: boolean
}

export const MemberSearchSelect: React.FC<MemberSearchSelectProps> = ({
  organizationId,
  value,
  onChange,
  initialOptions,
  disabledOptions = {},
  projectActiveUserIds,
  disabled = false,
  placeholder = '搜索姓名 / 用户名 / 邮箱',
  ariaLabel,
  className,
  emptyHint = '没有匹配的成员',
}) => {
  const [keyword, setKeyword] = useState('')
  const [results, setResults] = useState<OrganizationMember[]>([])
  const [loading, setLoading] = useState(false)
  const [opened, setOpened] = useState(false)
  const requestIdRef = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)

  // 防抖搜索：仅输入了关键字才请求后端；否则用调用方给的初始候选。
  useEffect(() => {
    const trimmed = keyword.trim()
    if (!opened || trimmed === '') {
      setResults([])
      setLoading(false)
      return
    }
    const requestId = ++requestIdRef.current
    setLoading(true)
    const timer = window.setTimeout(async () => {
      try {
        const response = await MemberApiService.getMembers(organizationId, {
          search: trimmed,
          limit: 50,
        })
        if (requestIdRef.current !== requestId) return
        setResults(response.members)
      } catch {
        if (requestIdRef.current !== requestId) return
        setResults([])
      } finally {
        if (requestIdRef.current === requestId) setLoading(false)
      }
    }, 300)
    return () => window.clearTimeout(timer)
  }, [keyword, opened, organizationId])

  // 点击外部关闭下拉。
  useEffect(() => {
    if (!opened) return
    const handlePointerDown = (event: PointerEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpened(false)
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [opened])

  const trimmedKeyword = keyword.trim()
  const options = useMemo(
    () => (trimmedKeyword === '' ? initialOptions : results),
    [initialOptions, results, trimmedKeyword],
  )

  const selectedMember = useMemo(() => {
    const pool = options.length > 0 ? options : initialOptions
    const fromPool = pool.find(member => member.user_id === value)
    if (fromPool) return fromPool
    return null
  }, [initialOptions, options, value])

  const handleSelect = useCallback((member: OrganizationMember) => {
    if (disabledOptions[member.user_id]) return
    onChange(member.user_id)
    setOpened(false)
    setKeyword('')
  }, [disabledOptions, onChange])

  const displayValue = selectedMember
    ? memberDisplayName(selectedMember)
    : value
      ? '已选成员'
      : ''

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <div className="flex h-9 w-full items-center gap-2 rounded-interactive border border-input bg-background px-3">
        <Search className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" aria-hidden />
        <input
          type="text"
          role="combobox"
          aria-expanded={opened}
          aria-label={ariaLabel}
          value={opened ? keyword : displayValue}
          placeholder={placeholder}
          disabled={disabled}
          onChange={event => setKeyword(event.target.value)}
          onFocus={() => setOpened(true)}
          onClick={() => setOpened(true)}
          className="h-full min-w-0 flex-1 bg-transparent text-body text-foreground outline-none placeholder:text-muted-foreground/70"
        />
        {loading && <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" aria-hidden />}
      </div>

      {opened && (
        <div
          role="listbox"
          className="absolute left-0 right-0 top-[calc(100%+4px)] z-50 max-h-64 overflow-y-auto rounded-interactive border border-border bg-popover py-1 shadow-lg"
        >
          {options.length === 0 ? (
            <p className="px-3 py-2 text-caption text-muted-foreground">
              {trimmedKeyword === ''
                ? '暂无可选成员'
                : loading ? '正在搜索…' : emptyHint}
            </p>
          ) : options.map(member => {
            const disabledReason =
              disabledOptions[member.user_id] ??
              (projectActiveUserIds && !projectActiveUserIds.has(member.user_id)
                ? '未加入项目'
                : undefined)
            const isSelected = member.user_id === value
            return (
              <button
                key={member.user_id}
                type="button"
                role="option"
                aria-selected={isSelected}
                disabled={Boolean(disabledReason)}
                onClick={() => handleSelect(member)}
                className={cn(
                  'flex w-full items-center gap-2 px-3 py-1.5 text-left text-body',
                  disabledReason
                    ? 'cursor-not-allowed text-muted-foreground/60'
                    : 'text-foreground hover:bg-accent',
                  isSelected && 'bg-accent',
                )}
              >
                <UserRound className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" aria-hidden />
                <span className="min-w-0 flex-1 truncate">
                  {memberDisplayName(member)}
                  {member.user?.email ? (
                    <span className="ml-1.5 text-caption text-muted-foreground/80">
                      {member.user.email}
                    </span>
                  ) : null}
                </span>
                {disabledReason && (
                  <span className="shrink-0 text-caption text-muted-foreground/70">
                    {disabledReason}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
