import { describe, expect, it } from 'vitest'
import type { ChatSession } from '@tabtin/chat-client'
import {
  decideAskNewSessionTarget,
  isReusableEmptyAskSession,
  resolveReusableEmptyAskSessionId,
} from '../askNewSessionTargetPolicy'

function session(partial: Partial<ChatSession> & { id: string }): ChatSession {
  return {
    title: null,
    space_id: 'space-1',
    agent_mode: 'ask',
    status: 'active',
    ...partial,
  } as ChatSession
}

describe('askNewSessionTargetPolicy ', () => {
  describe('isReusableEmptyAskSession', () => {
    it('treats message_count=0 / has_messages=false as reusable empty', () => {
      expect(isReusableEmptyAskSession(session({ id: 'a', message_count: 0, has_messages: false }))).toBe(true)
      expect(isReusableEmptyAskSession(session({ id: 'b', message_count: 0 }))).toBe(true)
    })

    it('rejects sessions with visible messages', () => {
      expect(isReusableEmptyAskSession(session({ id: 'c', message_count: 3 }))).toBe(false)
      expect(isReusableEmptyAskSession(session({ id: 'd', message_count: 0, has_messages: true }))).toBe(false)
    })

    it('rejects archived or non-ask sessions', () => {
      expect(isReusableEmptyAskSession(session({ id: 'e', message_count: 0, status: 'archived' }))).toBe(false)
      expect(isReusableEmptyAskSession(session({ id: 'f', message_count: 0, agent_mode: 'task' }))).toBe(false)
    })
  })

  describe('resolveReusableEmptyAskSessionId', () => {
    it('returns null when no empty sessions', () => {
      expect(resolveReusableEmptyAskSessionId([
        session({ id: 'a', message_count: 2 }),
      ])).toBeNull()
    })

    it('picks the most recent empty session by last_message_at', () => {
      const id = resolveReusableEmptyAskSessionId([
        session({ id: 'old-empty', message_count: 0, last_message_at: '2026-09-01T00:00:00Z' }),
        session({ id: 'busy', message_count: 5, last_message_at: '2026-09-14T00:00:00Z' }),
        session({ id: 'new-empty', message_count: 0, last_message_at: '2026-09-13T00:00:00Z' }),
      ])
      expect(id).toBe('new-empty')
    })

    it('prefers sessions without timestamp (treated as newest)', () => {
      const id = resolveReusableEmptyAskSessionId([
        session({ id: 'stamped', message_count: 0, last_message_at: '2026-09-13T00:00:00Z' }),
        session({ id: 'fresh', message_count: 0, last_message_at: null }),
      ])
      expect(id).toBe('fresh')
    })
  })

  describe('decideAskNewSessionTarget', () => {
    it('keeps active when current session is empty (no stacking)', () => {
      const decision = decideAskNewSessionTarget({
        activeSessionId: 'empty-active',
        askSessions: [
          session({ id: 'empty-active', message_count: 0 }),
          session({ id: 'done', message_count: 4 }),
        ],
      })
      expect(decision).toEqual({ action: 'keep_active', sessionId: 'empty-active' })
    })

    it('reuses the most recent empty session when active is non-empty', () => {
      const decision = decideAskNewSessionTarget({
        activeSessionId: 'busy-active',
        askSessions: [
          session({ id: 'busy-active', message_count: 7 }),
          session({ id: 'empty-1', message_count: 0, last_message_at: '2026-09-10T00:00:00Z' }),
          session({ id: 'empty-2', message_count: 0, last_message_at: '2026-09-12T00:00:00Z' }),
        ],
      })
      expect(decision).toEqual({ action: 'reuse_empty', sessionId: 'empty-2' })
    })

    it('creates when no empty session exists', () => {
      const decision = decideAskNewSessionTarget({
        activeSessionId: 'busy-active',
        askSessions: [session({ id: 'busy-active', message_count: 7 })],
      })
      expect(decision).toEqual({ action: 'create' })
    })

    it('reuses empty even when active is null', () => {
      const decision = decideAskNewSessionTarget({
        activeSessionId: null,
        askSessions: [session({ id: 'empty-1', message_count: 0 })],
      })
      expect(decision).toEqual({ action: 'reuse_empty', sessionId: 'empty-1' })
    })

    it('creates when list is empty', () => {
      expect(decideAskNewSessionTarget({ activeSessionId: null, askSessions: [] }))
        .toEqual({ action: 'create' })
    })

    it('falls back to reuse when active id is stale (not in list)', () => {
      const decision = decideAskNewSessionTarget({
        activeSessionId: 'ghost',
        askSessions: [session({ id: 'empty-1', message_count: 0 })],
      })
      expect(decision).toEqual({ action: 'reuse_empty', sessionId: 'empty-1' })
    })
  })
})
