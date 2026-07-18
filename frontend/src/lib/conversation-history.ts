import type { ChatMessage, ConversationSummary } from '@/types'

const HISTORY_KEY = 'stride:conversation-history:v1'
const LOCAL_MESSAGES_KEY = 'stride:conversation-messages:v1'

export function loadHistory(): ConversationSummary[] {
  try {
    const items = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]') as ConversationSummary[]
    if (!Array.isArray(items)) return []
    return items
      .filter((item) => item && typeof item.id === 'string' && typeof item.title === 'string')
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
  } catch {
    return []
  }
}

export function saveHistory(items: ConversationSummary[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 40)))
}

export function upsertHistory(
  current: ConversationSummary[],
  entry: ConversationSummary,
): ConversationSummary[] {
  const next = [entry, ...current.filter((item) => item.id !== entry.id)].sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt),
  )
  saveHistory(next)
  return next
}

export function titleFromQuery(query: string): string {
  const cleaned = query.replace(/\s+/g, ' ').trim()
  if (!cleaned) return 'New conversation'
  return cleaned.length > 42 ? `${cleaned.slice(0, 42).trimEnd()}…` : cleaned
}

export function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const diffMs = Date.now() - date.getTime()
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return 'Now'
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d`
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function loadLocalMessages(id: string): ChatMessage[] {
  try {
    const all = JSON.parse(localStorage.getItem(LOCAL_MESSAGES_KEY) ?? '{}') as Record<
      string,
      ChatMessage[]
    >
    return Array.isArray(all[id]) ? all[id] : []
  } catch {
    return []
  }
}

export function saveLocalMessages(id: string, messages: ChatMessage[]) {
  let all: Record<string, ChatMessage[]> = {}
  try {
    all = JSON.parse(localStorage.getItem(LOCAL_MESSAGES_KEY) ?? '{}') as Record<
      string,
      ChatMessage[]
    >
  } catch {
    // Replace invalid local data.
  }
  localStorage.setItem(LOCAL_MESSAGES_KEY, JSON.stringify({ ...all, [id]: messages }))
}
