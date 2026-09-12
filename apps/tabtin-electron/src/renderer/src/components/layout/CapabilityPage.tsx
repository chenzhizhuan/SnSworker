/**
 * CapabilityPage — 能力中心页面。
 *
 * 直接内嵌现有两个页面：
 *   - 能力库（CapabilityMarketplacePage，技能市场）
 *   - 连接器（TrackerPanel，自动化）
 * 不跳转、不弹全屏页，在当前画布内 Tab 切换展示。
 */

import React, { Suspense, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { BookText, Activity } from 'lucide-react'
import { cn } from '@utils/cn'
import { useSpaceStore } from '@stores/useSpaceStore'
import { useSkillLibraryContextSpaceId } from '@components/settings/panels/SkillLibraryPanel'

const CapabilityMarketplacePage = React.lazy(() =>
  import('@components/context-space/capability-marketplace/CapabilityMarketplacePage').then(
    m => ({ default: m.CapabilityMarketplacePage }),
  ),
)
const TrackerPanel = React.lazy(() =>
  import('@components/tabtracker/TrackerPanel').then(m => ({ default: m.TrackerPanel })),
)

type CapabilityTab = 'library' | 'connectors'

const CAPABILITY_TABS: Array<{
  id: CapabilityTab
  labelKey: string
  defaultLabel: string
  Icon: React.FC<{ className?: string; size?: number }>
}> = [
  { id: 'library', labelKey: 'sidebar:capability.library', defaultLabel: '能力库', Icon: BookText },
  { id: 'connectors', labelKey: 'sidebar:capability.connectors', defaultLabel: '连接器', Icon: Activity },
]

const LoadingFallback: React.FC = () => (
  <div className="flex h-full w-full items-center justify-center">
    <span className="block h-6 w-6 rounded-full border-2 border-border border-t-accent animate-spin" />
  </div>
)

export const CapabilityPage: React.FC = () => {
  const { t } = useTranslation(['sidebar'])
  const [activeTab, setActiveTab] = useState<CapabilityTab>('library')
  const skillSpaceId = useSkillLibraryContextSpaceId()
  const automationSpaceId = useSpaceStore((s) => s.selectedSpace?.id ?? null)

  const handleTabClick = useCallback((tab: CapabilityTab) => {
    setActiveTab(tab)
  }, [])

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      {/* Tab 栏 */}
      <div className="flex items-center gap-1 border-b border-border/40 px-4 pt-3 shrink-0">
        {CAPABILITY_TABS.map(({ id, labelKey, defaultLabel, Icon }) => {
          const active = activeTab === id
          return (
            <button
              key={id}
              type="button"
              onClick={() => handleTabClick(id)}
              className={cn(
                'flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm transition-colors',
                active
                  ? 'text-foreground border-b-2 border-accent font-medium'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              {t(labelKey, { defaultValue: defaultLabel })}
            </button>
          )
        })}
      </div>

      {/* 内容区 — 直接内嵌现有页面 */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'library' && (
          <Suspense fallback={<LoadingFallback />}>
            <CapabilityMarketplacePage spaceId={skillSpaceId} />
          </Suspense>
        )}
        {activeTab === 'connectors' && (
          <Suspense fallback={<LoadingFallback />}>
            {automationSpaceId ? (
              <TrackerPanel spaceId={automationSpaceId} detailNavigation="inline" />
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  {t('sidebar:capability.connectorsHint', { defaultValue: '请先选择一个工作空间' })}
                </p>
              </div>
            )}
          </Suspense>
        )}
      </div>
    </div>
  )
}

CapabilityPage.displayName = 'CapabilityPage'
