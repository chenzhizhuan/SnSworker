import { describe, expect, it } from 'vitest'
import type { ChatMessage } from '@tabtin/chat-client'
import { messageBubblePropsAreEqual } from '../messages/common/messageBubbleMemoCompare'

function msg(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'm1',
    role: 'assistant',
    content: 'hello',
    created_at: '2026-07-27T00:00:00Z',
    ...overrides,
  } as ChatMessage
}

describe('messageBubblePropsAreEqual', () => {
  it('壳字段相同 → true（不再因 timeTick 打穿）', () => {
    const message = msg()
    const base = {
      message,
      sessionId: 's1',
      isLastAssistantMsg: false,
      sessionPulseVisible: false,
      isLastInTurn: true,
    }
    expect(messageBubblePropsAreEqual(base, { ...base })).toBe(true)
  })

  it('content 变化 → false', () => {
    const prev = { message: msg({ content: 'a' }), sessionId: 's1' }
    const next = { message: msg({ content: 'b' }), sessionId: 's1' }
    expect(messageBubblePropsAreEqual(prev, next)).toBe(false)
  })

  it('#9341 error_info_json 变化 → false', () => {
    const prev = {
      message: msg({ error_info_json: { error_class: 'LLM_ERROR' } }),
      sessionId: 's1',
    }
    const next = {
      message: msg({
        error_info_json: {
          error_class: 'LLM_BILLING_ERROR',
          category: 'organization_insufficient_credits',
        },
      }),
      sessionId: 's1',
    }
    expect(messageBubblePropsAreEqual(prev, next)).toBe(false)
  })

  it('影响气泡渲染和交互的外部 props 变化 → false', () => {
    const message = msg()
    const base = {
      message,
      sessionId: 's1',
      tabScopeKey: 'conversation:s1',
      onFork: () => {},
      onContextBlockNavigate: () => {},
      onContextBlockContextMenu: () => {},
      userAlign: 'right' as const,
      previewMode: false,
    }
    const changedProps = [
      { tabScopeKey: 'conversation:s2' },
      { onFork: () => {} },
      { onContextBlockNavigate: () => {} },
      { onContextBlockContextMenu: () => {} },
      { userAlign: 'left' as const },
      { previewMode: true },
    ]

    for (const changed of changedProps) {
      expect(messageBubblePropsAreEqual(base, { ...base, ...changed })).toBe(false)
    }
  })

  it('流式 dogfood(2026-10-14)：timelineMessages 数组换引用但元素引用未变 → true（未变化气泡 memo 命中）', () => {
    // store upsertMessage 是 [...prev]; next[idx] = message —— 只有流式目标
    // 消息对象引用变化。未变化气泡的 message 引用相同，memo 必须命中，
    // 否则每个 token 批次打穿全部可见气泡（打字卡顿主因）。
    const userMsg = msg({ id: 'u1', role: 'user' })
    const otherMsg = msg({ id: 'm2' })
    const streamingPrev = msg({ id: 'm3', content: 'part' })
    const streamingNext = msg({ id: 'm3', content: 'partial' })

    const prev = {
      message: otherMsg,
      sessionId: 's1',
      timelineMessages: [userMsg, otherMsg, streamingPrev],
      timelineIndex: 1,
    }
    const next = {
      message: otherMsg,
      sessionId: 's1',
      timelineMessages: [userMsg, otherMsg, streamingNext],
      timelineIndex: 1,
    }
    expect(messageBubblePropsAreEqual(prev, next)).toBe(true)
  })

  it('流式 dogfood(2026-10-14)：timelineMessages 中本气泡消息对象被替换 → false（自身正确刷新）', () => {
    const userMsg = msg({ id: 'u1', role: 'user' })
    const streamingPrev = msg({ id: 'm3', content: 'part' })
    const streamingNext = msg({ id: 'm3', content: 'partial' })

    const prev = {
      message: streamingPrev,
      sessionId: 's1',
      timelineMessages: [userMsg, streamingPrev],
      timelineIndex: 1,
    }
    const next = {
      message: streamingNext,
      sessionId: 's1',
      timelineMessages: [userMsg, streamingNext],
      timelineIndex: 1,
    }
    expect(messageBubblePropsAreEqual(prev, next)).toBe(false)
  })

  it('timelineMessages 长度变化（新消息） → false', () => {
    const userMsg = msg({ id: 'u1', role: 'user' })
    const otherMsg = msg({ id: 'm2' })
    const added = msg({ id: 'm3' })
    const prev = { message: otherMsg, sessionId: 's1', timelineMessages: [userMsg, otherMsg] }
    const next = { message: otherMsg, sessionId: 's1', timelineMessages: [userMsg, otherMsg, added] }
    expect(messageBubblePropsAreEqual(prev, next)).toBe(false)
  })

  it('投影依赖变化：user 消息 attachments_json 变化 → false（filename map 依赖）', () => {
    const userBefore = msg({ id: 'u1', role: 'user', attachments_json: [{ file_id: 'f1' }] })
    const userAfter = msg({ id: 'u1', role: 'user', attachments_json: [{ file_id: 'f1' }, { file_id: 'f2' }] })
    const otherMsg = msg({ id: 'm2' })
    const prev = { message: otherMsg, sessionId: 's1', timelineMessages: [userBefore, otherMsg] }
    const next = { message: otherMsg, sessionId: 's1', timelineMessages: [userAfter, otherMsg] }
    expect(messageBubblePropsAreEqual(prev, next)).toBe(false)
  })

  it('投影依赖变化：消息 message_kind 变化 → false（轮末产物卡判定依赖）', () => {
    const before = msg({ id: 'm2', message_kind: 'llm' })
    const after = msg({ id: 'm2', message_kind: 'tool_artifact' })
    const userMsg = msg({ id: 'u1', role: 'user' })
    const prev = { message: before, sessionId: 's1', timelineMessages: [userMsg, before] }
    const next = { message: after, sessionId: 's1', timelineMessages: [userMsg, after] }
    expect(messageBubblePropsAreEqual(prev, next)).toBe(false)
  })
})
