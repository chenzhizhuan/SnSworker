/**
 * CapabilityPage — 能力中心页面。
 *
 * 直接内嵌 CapabilityMarketplacePage（其自带「技能 / 连接器」双 Tab，
 * 内含 SkillPanel marketplaceMode + McpPanel embedded，闭环完整）。
 * 不再额外包一层 Tab 栏，避免顶部双层 Tab 冗余。
 */

import React, { Suspense } from 'react'
import { useSkillLibraryContextSpaceId } from '@components/settings/panels/SkillLibraryPanel'

const CapabilityMarketplacePage = React.lazy(() =>
  import('@components/context-space/capability-marketplace/CapabilityMarketplacePage').then(
    m => ({ default: m.CapabilityMarketplacePage }),
  ),
)

const LoadingFallback: React.FC = () => (
  <div className="flex h-full w-full items-center justify-center">
    <span className="block h-6 w-6 rounded-full border-2 border-border border-t-accent animate-spin" />
  </div>
)

export const CapabilityPage: React.FC = () => {
  const skillSpaceId = useSkillLibraryContextSpaceId()

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <div className="flex-1 overflow-hidden">
        <Suspense fallback={<LoadingFallback />}>
          <CapabilityMarketplacePage spaceId={skillSpaceId} />
        </Suspense>
      </div>
    </div>
  )
}

CapabilityPage.displayName = 'CapabilityPage'
