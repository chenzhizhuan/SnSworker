/**
 * 问一句「新问答」目标策略（纯决策，无 store / HTTP / 副作用）
 *
 * 产品口径（2026-09-15 专哥提出）：从未问答过的空白任务不应堆积。
 * 连点「新问答」时：
 * 1. 当前激活会话本身就是空的 → 直接停在原地，不新建也不切换；
 * 2. 否则优先激活最近一个空白 ask 会话（单槽复用，避免堆空行）；
 * 3. 仅当不存在任何空白 ask 会话时才真正 create。
 *
 * 与办件事草稿单槽（draftSessionTargetPolicy）同思路，但问一句是
 * 「点击即激活」模型：目标是决定 activeSessionId 指哪，而非消息挂哪。
 * 编排与副作用见 AskPage.handleNewAsk。
 */

import type { ChatSession } from '@tabtin/chat-client'
import { sessionHasVisibleMessages } from '../../stores/chat/session/sessionHasVisibleMessages'

export type AskSessionLike = Pick<
  ChatSession,
  'id' | 'has_messages' | 'message_count' | 'last_message_at' | 'status' | 'agent_mode'
>

export type AskNewSessionDecision =
  | { action: 'keep_active'; sessionId: string }
  | { action: 'reuse_empty'; sessionId: string }
  | { action: 'create' }

/** 空白 ask 会话：无可见消息、未归档、agent_mode 匹配 ask 池 */
export function isReusableEmptyAskSession(session: AskSessionLike): boolean {
  if (session.status === 'archived') return false
  if (session.agent_mode && session.agent_mode !== 'ask') return false
  return !sessionHasVisibleMessages(session)
}

/**
 * 从 ask 会话列表里挑最近一个空白会话（按 last_message_at 降序，无时间戳排最前）。
 * 列表应只含本工作空间 agent_mode='ask' 的 active 会话。
 */
export function resolveReusableEmptyAskSessionId(
  sessions: ReadonlyArray<AskSessionLike>,
): string | null {
  const empties = sessions.filter(isReusableEmptyAskSession)
  if (empties.length === 0) return null
  empties.sort((a, b) => {
    const ta = a.last_message_at ? new Date(a.last_message_at).getTime() : Number.POSITIVE_INFINITY
    const tb = b.last_message_at ? new Date(b.last_message_at).getTime() : Number.POSITIVE_INFINITY
    // 时间戳倒序（最近的在前）；无时间戳视为最新
    if (ta === tb) return 0
    return ta === Number.POSITIVE_INFINITY || tb === Number.POSITIVE_INFINITY
      ? (ta === Number.POSITIVE_INFINITY ? -1 : 1)
      : tb - ta
  })
  return empties[0]?.id ?? null
}

/**
 * 「新问答」点击决策：
 * - active 空白 → keep_active（点击无感，停在当前空会话）
 * - active 非空 → reuse_empty（切到最近空白）或 create
 */
export function decideAskNewSessionTarget(input: {
  activeSessionId: string | null | undefined
  askSessions: ReadonlyArray<AskSessionLike>
}): AskNewSessionDecision {
  // 1. 当前激活会话空白：停在原地
  if (input.activeSessionId) {
    const active = input.askSessions.find(s => s.id === input.activeSessionId)
    if (active && isReusableEmptyAskSession(active)) {
      return { action: 'keep_active', sessionId: active.id }
    }
  }

  // 2. 优先复用最近一个空白 ask 会话
  const reusableId = resolveReusableEmptyAskSessionId(input.askSessions)
  if (reusableId) {
    return { action: 'reuse_empty', sessionId: reusableId }
  }

  // 3. 无空白会话：新建
  return { action: 'create' }
}
