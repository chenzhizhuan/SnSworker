/**
 * CapabilityPage — 能力中心页面。
 *
 * 技能和连接器从任务域二级入口升格为一级菜单。
 * 下设 Tab：能力库（现有技能市场）、连接器（现有连接器管理）、
 * 我的能力（技能成长线）、口径本、战法区。
 * 当前一期只渲染能力库和连接器（搬迁现有页面），其余 Tab 为占位。
 */

import React, { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { BookText, Plug, Sparkles, BookMarked, Target } from 'lucide-react'
import { cn } from '@utils/cn'
import {
  openSkillLibrary,
} from '@/services/agentMemoryNavigation'
import { SHELL_CANVAS_CARD_CLASS } from './shellUi'

type CapabilityTab = 'library' | 'connectors' | 'my-capability' | 'playbook' | 'strategy'

const CAPABILITY_TABS: Array<{
  id: CapabilityTab
  labelKey: string
  defaultLabel: string
  Icon: React.FC<{ className?: string; size?: number }>
}> = [
  { id: 'library', labelKey: 'sidebar:capability.library', defaultLabel: '能力库', Icon: BookText },
  { id: 'connectors', labelKey: 'sidebar:capability.connectors', defaultLabel: '连接器', Icon: Plug },
  { id: 'my-capability', labelKey: 'sidebar:capability.myCapability', defaultLabel: '我的能力', Icon: Sparkles },
  { id: 'playbook', labelKey: 'sidebar:capability.playbook', defaultLabel: '口径本', Icon: BookMarked },
  { id: 'strategy', labelKey: 'sidebar:capability.strategy', defaultLabel: '战法区', Icon: Target },
]

export const CapabilityPage: React.FC = () => {
  const { t } = useTranslation(['sidebar'])
  const [activeTab, setActiveTab] = useState<CapabilityTab>('library')

  const handleTabClick = useCallback((tab: CapabilityTab) => {
    if (tab === 'library') {
      // 能力库复用现有技能库全屏页
      openSkillLibrary()
      return
    }
    setActiveTab(tab)
  }, [])

  return (
    <div className={`flex h-full w-full flex-col overflow-hidden ${SHELL_CANVAS_CARD_CLASS}`}>
      {/* Tab 栏 */}
      <div className="flex items-center gap-1 border-b border-border/40 px-4 pt-3">
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

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'library' && (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <BookText className="mx-auto h-10 w-10 text-muted-foreground/30" />
              <p className="mt-3 text-sm text-muted-foreground">
                {t('sidebar:capability.libraryHint', { defaultValue: '点击上方「能力库」进入技能市场' })}
              </p>
            </div>
          </div>
        )}
        {activeTab === 'connectors' && (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <Plug className="mx-auto h-10 w-10 text-muted-foreground/30" />
              <p className="mt-3 text-sm text-muted-foreground">
                {t('sidebar:capability.connectorsHint', { defaultValue: '连接器管理即将上线' })}
              </p>
            </div>
          </div>
        )}
        {activeTab === 'my-capability' && (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <Sparkles className="mx-auto h-10 w-10 text-muted-foreground/30" />
              <p className="mt-3 text-sm text-muted-foreground">
                {t('sidebar:capability.myCapabilityHint', { defaultValue: '技能成长线即将上线' })}
              </p>
            </div>
          </div>
        )}
        {activeTab === 'playbook' && (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <BookMarked className="mx-auto h-10 w-10 text-muted-foreground/30" />
              <p className="mt-3 text-sm text-muted-foreground">
                {t('sidebar:capability.playbookHint', { defaultValue: '口径本即将上线' })}
              </p>
            </div>
          </div>
        )}
        {activeTab === 'strategy' && (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <Target className="mx-auto h-10 w-10 text-muted-foreground/30" />
              <p className="mt-3 text-sm text-muted-foreground">
                {t('sidebar:capability.strategyHint', { defaultValue: '战法区即将上线' })}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

CapabilityPage.displayName = 'CapabilityPage'
