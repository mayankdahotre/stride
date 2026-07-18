import { describe, expect, it } from 'vitest'
import { parseSSEChunk } from '@/api/conversation'

describe('conversation SSE parser', () => {
  it('parses typed JSON and token events while retaining partial input', () => {
    const parsed = parseSSEChunk(
      'event: metadata\ndata: {"thread_id":"t1"}\n\nevent: token\ndata: Fast shoes\n\nevent: done\ndata: {"message":{"content":"Complete"}}\n\nevent: sta',
    )
    expect(parsed.events).toEqual([
      { event: 'metadata', data: { thread_id: 't1' } },
      { event: 'token', data: 'Fast shoes' },
      { event: 'done', data: { message: { content: 'Complete' } } },
    ])
    expect(parsed.remainder).toBe('event: sta')
  })

  it('supports multiline SSE data', () => {
    const parsed = parseSSEChunk('event: token\ndata: first\ndata: second\n\n')
    expect(parsed.events[0]).toEqual({ event: 'token', data: 'first\nsecond' })
  })
})
