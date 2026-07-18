import type { ChatMessage, Conversation, Intent, StreamEvent } from '@/types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined
const TOKEN_KEY = 'stride:conversation-tokens:v1'

function headers(token?: string): HeadersInit {
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'X-Conversation-Token': token } : {}),
    ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
  }
}

function ensureOk(response: Response) {
  if (!response.ok) throw new Error(`Request failed (${response.status})`)
  return response
}

export function getStoredToken(threadId: string): string | undefined {
  try {
    const tokens = JSON.parse(localStorage.getItem(TOKEN_KEY) ?? '{}') as Record<string, string>
    return tokens[threadId]
  } catch {
    return undefined
  }
}

export function storeToken(threadId: string, token: string) {
  let tokens: Record<string, string> = {}
  try {
    tokens = JSON.parse(localStorage.getItem(TOKEN_KEY) ?? '{}') as Record<string, string>
  } catch {
    // Replace invalid local data.
  }
  localStorage.setItem(TOKEN_KEY, JSON.stringify({ ...tokens, [threadId]: token }))
}

export async function createConversation(signal?: AbortSignal): Promise<Conversation> {
  const response = ensureOk(
    await fetch(`${API_BASE}/api/v1/conversations`, {
      method: 'POST',
      headers: headers(),
      signal,
    }),
  )
  const conversation = (await response.json()) as Conversation
  storeToken(conversation.thread_id, conversation.conversation_token)
  return conversation
}

export async function getConversation(
  threadId: string,
  signal?: AbortSignal,
): Promise<{
  thread_id: string
  title: string
  created_at: string
  messages: Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    created_at: string
    envelope?: Record<string, unknown> | null
  }>
}> {
  const token = getStoredToken(threadId)
  if (!token) throw new Error('Conversation token is unavailable')
  const response = ensureOk(
    await fetch(`${API_BASE}/api/v1/conversations/${threadId}`, {
      headers: headers(token),
      signal,
    }),
  )
  return response.json()
}

export function mapApiMessages(
  messages: Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    created_at: string
    envelope?: Record<string, unknown> | null
  }>,
): ChatMessage[] {
  return messages.map((message) => {
    const envelope = message.envelope ?? undefined
    return {
      id: String(message.id),
      role: message.role,
      content: message.content,
      createdAt: message.created_at,
      products: Array.isArray(envelope?.products) ? (envelope.products as ChatMessage['products']) : undefined,
      comparison: envelope?.comparison
        ? ((envelope.comparison as { products?: ChatMessage['comparison'] }).products ??
          (Array.isArray(envelope.comparison) ? (envelope.comparison as ChatMessage['comparison']) : undefined))
        : undefined,
      recommendation:
        typeof envelope?.recommendation === 'string'
          ? envelope.recommendation
          : envelope?.recommendation && typeof envelope.recommendation === 'object'
            ? String((envelope.recommendation as { reason?: string }).reason ?? '')
            : undefined,
      plan: Array.isArray(envelope?.plan)
        ? (envelope.plan as ChatMessage['plan'])
        : envelope?.plan && typeof envelope.plan === 'object' && Array.isArray((envelope.plan as { items?: unknown }).items)
          ? ((envelope.plan as { items: ChatMessage['plan'] }).items)
          : undefined,
    }
  })
}

export function parseSSEChunk(buffer: string): {
  events: StreamEvent[]
  remainder: string
} {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const blocks = normalized.split('\n\n')
  const remainder = blocks.pop() ?? ''
  const events = blocks.flatMap((block): StreamEvent[] => {
    let event: StreamEvent['event'] = 'token'
    const dataLines: string[] = []
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim() as StreamEvent['event']
      if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
    }
    if (!dataLines.length) return []
    const raw = dataLines.join('\n')
    let data: unknown = raw
    try {
      data = JSON.parse(raw)
    } catch {
      // Token events can be plain text.
    }
    return [{ event, data }]
  })
  return { events, remainder }
}

export async function streamMessage(
  threadId: string,
  content: string,
  requestId: string,
  intent: Intent | undefined,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
) {
  const token = getStoredToken(threadId)
  if (!token) throw new Error('Conversation token is unavailable')
  const response = ensureOk(
    await fetch(`${API_BASE}/api/v1/conversations/${threadId}/messages/stream`, {
      method: 'POST',
      headers: headers(token),
      body: JSON.stringify({
        content,
        request_id: requestId,
        ...(intent ? { intent } : {}),
      }),
      signal,
    }),
  )
  if (!response.body) throw new Error('Streaming is not supported by this response')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const parsed = parseSSEChunk(buffer)
    buffer = parsed.remainder
    parsed.events.forEach(onEvent)
    if (done) break
  }
  if (buffer.trim()) {
    parseSSEChunk(`${buffer}\n\n`).events.forEach(onEvent)
  }
}
