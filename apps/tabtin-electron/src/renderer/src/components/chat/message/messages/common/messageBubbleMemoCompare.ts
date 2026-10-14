import type { ChatMessage } from '@tabtin/chat-client'
import type { LocalChatMessage } from '@stores/chat/shared/types'

type BubbleComparableProps = {
  message: ChatMessage
  sessionId?: string | null
  tabScopeKey?: string | null
  subagentRunSessionId?: string | null
  isLastAssistantMsg?: boolean
  sessionPulseVisible?: boolean
  isLastInTurn?: boolean
  onFork?: unknown
  onContextBlockNavigate?: unknown
  onContextBlockContextMenu?: unknown
  userAlign?: unknown
  previewMode?: boolean
  hideAgentBadge?: boolean
  highlightedMessageId?: string | null
  highlightKey?: string
  isMini?: boolean
  isSameTurnAssistant?: boolean
  timelineMessages?: unknown
  timelineIndex?: number
  includeSubagentMessages?: boolean
  timelineIsStreaming?: boolean
  contentBlocksOverride?: unknown
  turnArtifacts?: unknown
  historyArtifacts?: unknown
  onUserMessageExpand?: unknown
  accessCapabilities?: unknown
}

/**
 * timelineMessages 消费点投影比较。
 *
 * 流式输出时 store 的 upsertMessage 是 `[...prev]; next[idx] = message`——
 * 数组与流式目标消息对象每个 token 都换引用。气泡对 timelineMessages 的
 * 实际消费只有两处（dogfood 2026-10-14 性能排查）：
 *   1. collectAttachmentFilenameById —— 只读 user 消息的 id + attachments_json
 *   2. shouldShowTurnArtifactsCard —— 只读消息的 role + message_kind
 *      （isRegularUserMessage / canHostTurnArtifacts 的判定输入）
 * 旧的全数组引用比较会让每个 token 批次打穿全部可见气泡的 memo（连带
 * Markdown 重新解析），是打字卡顿的主因。改为只比较上述投影；流式消息
 * 自身仍靠上方 message.content / content_blocks_json 比较正确刷新。
 */
type TimelineMessageProjection = {
  id: unknown
  role: unknown
  message_kind: unknown
  attachments_json: unknown
}

function timelineMessageProjectionAt(
  messages: readonly unknown[],
  index: number,
): TimelineMessageProjection | null {
  const message = messages[index]
  if (message === null || typeof message !== 'object') return null
  const record = message as Record<string, unknown>
  return {
    id: record.id,
    role: record.role,
    message_kind: record.message_kind,
    attachments_json: record.attachments_json,
  }
}

function timelineMessagesEqual(prev: unknown, next: unknown): boolean {
  if (prev === next) return true
  if (!Array.isArray(prev) || !Array.isArray(next)) return false
  if (prev.length !== next.length) return false
  for (let i = 0; i < prev.length; i++) {
    const a = timelineMessageProjectionAt(prev, i)
    const b = timelineMessageProjectionAt(next, i)
    if (a === null || b === null) {
      if (prev[i] !== next[i]) return false
      continue
    }
    if (
      a.id !== b.id
      || a.role !== b.role
      || a.message_kind !== b.message_kind
      || a.attachments_json !== b.attachments_json
    ) {
      return false
    }
  }
  return true
}

// eslint-disable-next-line complexity -- memo 比较必须显式列出会影响气泡展示的字段，避免隐式浅比较漏刷新。
function firstUnequalField(
  prev: BubbleComparableProps,
  next: BubbleComparableProps,
): string | null {
  if (prev.message.id !== next.message.id) return 'message.id'
  if (prev.message.content !== next.message.content) return 'message.content'
  if (prev.message.intent !== next.message.intent) return 'message.intent'
  if (prev.message.attachments_json !== next.message.attachments_json) {
    return 'message.attachments_json'
  }
  if (prev.message.content_blocks_json !== next.message.content_blocks_json) {
    return 'message.content_blocks_json'
  }
  if (prev.message.metadata !== next.message.metadata) return 'message.metadata'
  // ：终态错误正典在 error_info_json；漏比会导致卡不刷新。
  if (prev.message.error_info_json !== next.message.error_info_json) {
    return 'message.error_info_json'
  }
  if (prev.message.checkpoint_hash !== next.message.checkpoint_hash) {
    return 'message.checkpoint_hash'
  }
  if (prev.message.checkpoint_record !== next.message.checkpoint_record) {
    return 'message.checkpoint_record'
  }
  if (prev.message.agent_run_id !== next.message.agent_run_id) {
    return 'message.agent_run_id'
  }
  if (prev.message.diff_summary !== next.message.diff_summary) {
    return 'message.diff_summary'
  }
  if (prev.message.error_code !== next.message.error_code) return 'message.error_code'
  if (prev.message.message_kind !== next.message.message_kind) {
    return 'message.message_kind'
  }
  if (
    (prev.message as LocalChatMessage).sendStatus
    !== (next.message as LocalChatMessage).sendStatus
  ) {
    return 'message.sendStatus'
  }
  if (prev.sessionId !== next.sessionId) return 'sessionId'
  if (prev.tabScopeKey !== next.tabScopeKey) return 'tabScopeKey'
  if (prev.subagentRunSessionId !== next.subagentRunSessionId) {
    return 'subagentRunSessionId'
  }
  if (prev.isLastAssistantMsg !== next.isLastAssistantMsg) return 'isLastAssistantMsg'
  if (prev.sessionPulseVisible !== next.sessionPulseVisible) return 'sessionPulseVisible'
  if (prev.isLastInTurn !== next.isLastInTurn) return 'isLastInTurn'
  if (prev.onFork !== next.onFork) return 'onFork'
  if (prev.onContextBlockNavigate !== next.onContextBlockNavigate) {
    return 'onContextBlockNavigate'
  }
  if (prev.onContextBlockContextMenu !== next.onContextBlockContextMenu) {
    return 'onContextBlockContextMenu'
  }
  if (prev.userAlign !== next.userAlign) return 'userAlign'
  if (prev.previewMode !== next.previewMode) return 'previewMode'
  if (prev.hideAgentBadge !== next.hideAgentBadge) return 'hideAgentBadge'
  if (prev.highlightedMessageId !== next.highlightedMessageId) {
    return 'highlightedMessageId'
  }
  if (prev.highlightKey !== next.highlightKey) return 'highlightKey'
  if (prev.isMini !== next.isMini) return 'isMini'
  if (prev.isSameTurnAssistant !== next.isSameTurnAssistant) {
    return 'isSameTurnAssistant'
  }
  if (!timelineMessagesEqual(prev.timelineMessages, next.timelineMessages)) {
    return 'timelineMessages'
  }
  if (prev.timelineIndex !== next.timelineIndex) return 'timelineIndex'
  if (prev.includeSubagentMessages !== next.includeSubagentMessages) {
    return 'includeSubagentMessages'
  }
  if (prev.timelineIsStreaming !== next.timelineIsStreaming) {
    return 'timelineIsStreaming'
  }
  if (prev.contentBlocksOverride !== next.contentBlocksOverride) {
    return 'contentBlocksOverride'
  }
  if (prev.turnArtifacts !== next.turnArtifacts) return 'turnArtifacts'
  if (prev.historyArtifacts !== next.historyArtifacts) return 'historyArtifacts'
  if (prev.onUserMessageExpand !== next.onUserMessageExpand) return 'onUserMessageExpand'
  if (prev.accessCapabilities !== next.accessCapabilities) return 'accessCapabilities'
  return null
}

export function messageBubblePropsAreEqual(
  prev: BubbleComparableProps,
  next: BubbleComparableProps,
): boolean {
  // 相对时间由 MessageTimeTickContext + 叶子组件订阅，不进气泡 props / memo
  return firstUnequalField(prev, next) === null
}
