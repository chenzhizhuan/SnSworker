/**
 * AskPage — 问一句页面（轻量即时问答入口）。
 *
 * 不建任务、不助手承办、无交付物。用户输入问题后只进"最近问答"历史，
 * 可一键转办件事。对标 13481「问一句」模式页面。
 */

import React, { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowRight, MessageSquare, Search } from 'lucide-react'
import { useMainNavStore } from '@stores/useMainNavStore'
import { useSpaceStore } from '@stores/useSpaceStore'
import { useSpaceViewPrefsStore } from '@stores/useSpaceViewPrefsStore'
import { resetNewTaskDraftUi } from './resetNewTaskDraftUi'
import { useChatStore } from '@stores/chat/useChatStore'
import { resolveDefaultExecutionWorkspaceId } from '@/utils/defaultExecutionSpace'
import { useOrganizationStore } from '@stores/useOrganizationStore'
import {
  resolvePersonalHomeConversationSpaceId,
} from './primaryNavigation'
import { SHELL_CANVAS_CARD_CLASS } from './shellUi'

interface RecentQA {
  id: string
  question: string
  timestamp: number
}

const MOCK_RECENT_QA: RecentQA[] = []

export const AskPage: React.FC = () => {
  const { t } = useTranslation(['sidebar'])
  const [input, setInput] = useState('')
  const organizationId = useOrganizationStore(state => state.selectedOrganization?.id ?? null)
  const spaces = useSpaceStore(state => state.spaces)
  const lastUsedWorkspaceId = useSpaceViewPrefsStore(state =>
    state.getLastUsedWorkspaceId(organizationId),
  )
  const setCurrentTab = useMainNavStore(state => state.setCurrentTab)

  const personalConversationSpaceId = resolvePersonalHomeConversationSpaceId({
    executionSpaceId: null,
    defaultPersonalWorkspaceId: resolveDefaultExecutionWorkspaceId(
      organizationId,
      spaces,
      lastUsedWorkspaceId,
    ),
  })

  const handleAsk = useCallback(() => {
    if (!input.trim()) return
    // 轻问答：直接在当前工作空间发起一个对话
    if (personalConversationSpaceId) {
      resetNewTaskDraftUi(personalConversationSpaceId)
      useChatStore.getState().startDraftSessionForSpace(personalConversationSpaceId, true)
      // 将用户输入作为第一条消息发送
      // TODO: 接入实际发送逻辑
    }
  }, [input, personalConversationSpaceId])

  const handleConvertToTask = useCallback(() => {
    if (!personalConversationSpaceId) return
    resetNewTaskDraftUi(personalConversationSpaceId)
    useChatStore.getState().startDraftSessionForSpace(personalConversationSpaceId, true)
    setCurrentTab('agent')
  }, [input, personalConversationSpaceId, setCurrentTab])

  return (
    <div className={`flex h-full w-full flex-col overflow-hidden ${SHELL_CANVAS_CARD_CLASS}`}>
      {/* 顶部标题区 */}
      <div className="px-8 pt-8 pb-4">
        <h1 className="text-xl font-medium text-foreground">
          {t('sidebar:ask.title', { defaultValue: '问一句' })}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t('sidebar:ask.subtitle', { defaultValue: '快速提问，不建任务、不生成交付物。需要深入处理可一键转为办件事。' })}
        </p>
      </div>

      {/* 输入区 */}
      <div className="px-8 pb-4">
        <div className="relative flex items-center gap-2 rounded-lg border border-border/60 bg-background px-4 py-3 focus-within:border-accent/50 transition-colors">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleAsk()
              }
            }}
            placeholder={t('sidebar:ask.placeholder', { defaultValue: '输入你的问题…' })}
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground/50"
          />
          {input.trim() && (
            <button
              type="button"
              onClick={handleConvertToTask}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/30 transition-colors"
              title={t('sidebar:ask.convertToTask', { defaultValue: '转为办件事' })}
            >
              {t('sidebar:ask.convertToTask', { defaultValue: '转为办件事' })}
              <ArrowRight className="h-3 w-3" aria-hidden />
            </button>
          )}
        </div>
      </div>

      {/* 大家常问 */}
      <div className="px-8 pb-3">
        <span className="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">
          {t('sidebar:ask.popular', { defaultValue: '大家常问' })}
        </span>
      </div>
      <div className="px-8 pb-6 flex flex-wrap gap-2">
        {[
          '如何创建工作空间？',
          '怎么导入外部数据？',
          '技能和连接器有什么区别？',
          '如何分享文档给团队成员？',
        ].map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => setInput(q)}
            className="rounded-full border border-border/40 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:border-accent/40 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* 最近问答 */}
      <div className="px-8 pb-2">
        <span className="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">
          {t('sidebar:ask.recent', { defaultValue: '最近问答' })}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto px-8 pb-8">
        {MOCK_RECENT_QA.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-center">
              <MessageSquare className="h-8 w-8 text-muted-foreground/30" aria-hidden />
              <p className="text-sm text-muted-foreground/50">
                {t('sidebar:ask.empty', { defaultValue: '还没有问答记录，输入问题开始吧' })}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {MOCK_RECENT_QA.map((qa) => (
              <div
                key={qa.id}
                className="rounded-lg border border-border/40 p-3 hover:border-border/60 transition-colors"
              >
                <p className="text-sm font-medium text-foreground">{qa.question}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

AskPage.displayName = 'AskPage'
