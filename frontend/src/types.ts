export type Intent = 'search' | 'compare' | 'recommend' | 'plan'

export interface Product {
  id: string
  name: string
  brand?: string
  description?: string
  category?: string
  image?: string
  price: number
  currency?: string
  rating?: number
  reviews?: number
  merchant?: string
  url?: string
}

export interface PlanStep {
  title: string
  description?: string
  status?: 'complete' | 'active' | 'upcoming'
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  products?: Product[]
  comparison?: Product[]
  recommendation?: string
  plan?: PlanStep[]
  status?: string
  isDemo?: boolean
}

export interface Conversation {
  thread_id: string
  conversation_token: string
  title: string
  created_at: string
}

export interface ConversationSummary {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  source: 'live' | 'local'
}

export type StreamEventName =
  | 'metadata'
  | 'status'
  | 'products'
  | 'comparison'
  | 'recommendation'
  | 'plan'
  | 'token'
  | 'done'
  | 'error'

export interface StreamEvent {
  event: StreamEventName
  data: unknown
}
