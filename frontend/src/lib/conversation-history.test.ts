import { describe, expect, it } from 'vitest'
import {
  loadHistory,
  titleFromQuery,
  upsertHistory,
} from '@/lib/conversation-history'
import type { ConversationSummary } from '@/types'

describe('conversation history', () => {
  it('upserts and persists recent conversations without dummy placeholders', () => {
    expect(loadHistory()).toEqual([])
    const first: ConversationSummary = {
      id: 'local-1',
      title: titleFromQuery('running shoes under 8000'),
      createdAt: '2026-07-18T01:00:00.000Z',
      updatedAt: '2026-07-18T01:00:00.000Z',
      source: 'local',
    }
    const next = upsertHistory([], first)
    expect(next).toHaveLength(1)
    expect(next[0]?.title).toBe('running shoes under 8000')
    expect(loadHistory()).toHaveLength(1)
  })
})
