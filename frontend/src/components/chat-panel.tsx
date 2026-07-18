import {
  ArrowUp,
  Bot,
  GitCompareArrows,
  Lightbulb,
  ListChecks,
  LoaderCircle,
  Menu,
  PanelLeft,
  PanelRight,
  RotateCcw,
  Search,
  ShoppingBag,
  Sparkles,
} from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import {
  createConversation,
  getConversation,
  mapApiMessages,
  streamMessage,
} from '@/api/conversation'
import { ProductCard } from '@/components/product-card'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { demoReply, welcomeMessage } from '@/data/demo'
import {
  loadLocalMessages,
  saveLocalMessages,
  titleFromQuery,
} from '@/lib/conversation-history'
import { cn } from '@/lib/utils'
import type {
  ChatMessage,
  ConversationSummary,
  Intent,
  PlanStep,
  Product,
  StreamEvent,
} from '@/types'

const intents: { value: Intent; label: string; icon: typeof Search }[] = [
  { value: 'search', label: 'Search', icon: Search },
  { value: 'compare', label: 'Compare', icon: GitCompareArrows },
  { value: 'recommend', label: 'Recommend', icon: Lightbulb },
  { value: 'plan', label: 'Plan', icon: ListChecks },
]

function eventPayload<T>(data: unknown, key: string): T | undefined {
  if (data && typeof data === 'object' && key in data) {
    return (data as Record<string, unknown>)[key] as T
  }
  return data as T
}

function assistantFromDone(data: unknown, fallback: ChatMessage): ChatMessage {
  const payload = eventPayload<Partial<ChatMessage>>(data, 'message')
  const envelope = data && typeof data === 'object' ? (data as Record<string, unknown>) : {}
  return {
    ...fallback,
    ...payload,
    id: payload?.id ?? fallback.id,
    role: 'assistant',
    createdAt: payload?.createdAt ?? fallback.createdAt,
    products: payload?.products ?? (envelope.products as Product[] | undefined) ?? fallback.products,
    comparison:
      payload?.comparison ??
      ((envelope.comparison as { products?: Product[] } | undefined)?.products ??
        (Array.isArray(envelope.comparison) ? (envelope.comparison as Product[]) : undefined)) ??
      fallback.comparison,
    recommendation:
      payload?.recommendation ??
      (typeof envelope.recommendation === 'string'
        ? envelope.recommendation
        : envelope.recommendation && typeof envelope.recommendation === 'object'
          ? String((envelope.recommendation as { reason?: string }).reason ?? '')
          : undefined) ??
      fallback.recommendation,
    plan:
      payload?.plan ??
      (Array.isArray(envelope.plan)
        ? (envelope.plan as PlanStep[])
        : envelope.plan && typeof envelope.plan === 'object'
          ? ((envelope.plan as { items?: PlanStep[] }).items ?? fallback.plan)
          : fallback.plan),
  }
}

export function ChatPanel({
  conversationId,
  cartCount = 0,
  sidebarCollapsed = false,
  cartCollapsed = false,
  onOpenSidebar,
  onOpenCart,
  onConversationUpsert,
  onResetConversation,
}: {
  conversationId?: string | null
  cartCount?: number
  sidebarCollapsed?: boolean
  cartCollapsed?: boolean
  onOpenSidebar: () => void
  onOpenCart: () => void
  onConversationUpsert: (summary: ConversationSummary) => void
  onResetConversation: () => void
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage])
  const [intent, setIntent] = useState<Intent | undefined>()
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [notice, setNotice] = useState('')
  const [threadId, setThreadId] = useState<string | undefined>(conversationId ?? undefined)
  const [selected, setSelected] = useState<Product[]>([])
  const [hydrating, setHydrating] = useState(Boolean(conversationId))
  const lastQuery = useRef('')
  const createdAtRef = useRef(new Date().toISOString())
  const skipHydrateForIdRef = useRef<string | null>(null)

  useEffect(() => {
    if (!conversationId) return

    if (skipHydrateForIdRef.current === conversationId) {
      skipHydrateForIdRef.current = null
      return
    }

    const activeConversationId = conversationId
    const controller = new AbortController()
    setHydrating(true)
    setNotice('')
    setSelected([])

    async function hydrate() {
      try {
        if (activeConversationId.startsWith('local-')) {
          const local = loadLocalMessages(activeConversationId)
          setMessages(local.length ? local : [welcomeMessage])
          setThreadId(activeConversationId)
          return
        }
        const conversation = await getConversation(activeConversationId, controller.signal)
        const mapped = mapApiMessages(conversation.messages)
        setMessages(mapped.length ? mapped : [welcomeMessage])
        setThreadId(activeConversationId)
        createdAtRef.current = conversation.created_at
      } catch {
        const local = loadLocalMessages(activeConversationId)
        setMessages(local.length ? local : [welcomeMessage])
        setThreadId(activeConversationId)
        setNotice(
          'Couldn’t reload that conversation from the server. Showing local copy if available.',
        )
      } finally {
        setHydrating(false)
      }
    }

    void hydrate()
    return () => controller.abort()
  }, [conversationId])

  const reset = () => {
    onResetConversation()
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    const query = content.trim() || lastQuery.current
    if (!query || loading || hydrating) return
    lastQuery.current = query

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      createdAt: new Date().toISOString(),
    }
    let nextMessages = messages
    if (content.trim()) {
      const withoutWelcome =
        messages.length === 1 && messages[0]?.id === welcomeMessage.id ? [] : messages
      nextMessages = [...withoutWelcome, userMessage]
      setMessages(nextMessages)
      setContent('')
    }

    setLoading(true)
    setNotice('')
    const draft: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
    }

    const stampHistory = (id: string, source: ConversationSummary['source']) => {
      const now = new Date().toISOString()
      skipHydrateForIdRef.current = id
      onConversationUpsert({
        id,
        title: titleFromQuery(query),
        createdAt: createdAtRef.current || now,
        updatedAt: now,
        source,
      })
    }

    try {
      let activeThread = threadId
      if (!activeThread || activeThread.startsWith('local-')) {
        const conversation = await createConversation()
        activeThread = conversation.thread_id
        setThreadId(activeThread)
        createdAtRef.current = conversation.created_at
      }

      let completed: ChatMessage | undefined
      const applyEvent = ({ event: eventName, data }: StreamEvent) => {
        if (eventName === 'error') {
          throw new Error(String(eventPayload(data, 'message') ?? 'Stream error'))
        }
        if (eventName === 'token') draft.content += String(eventPayload(data, 'token') ?? '')
        if (eventName === 'status') draft.status = String(eventPayload(data, 'status') ?? data)
        if (eventName === 'products') draft.products = eventPayload<Product[]>(data, 'products')
        if (eventName === 'comparison') {
          const comparison = eventPayload<{ products?: Product[] } | Product[]>(data, 'comparison')
          draft.comparison = Array.isArray(comparison)
            ? comparison
            : comparison?.products
        }
        if (eventName === 'recommendation') {
          const recommendation = eventPayload<{ reason?: string } | string>(data, 'recommendation')
          draft.recommendation =
            typeof recommendation === 'string'
              ? recommendation
              : recommendation?.reason
        }
        if (eventName === 'plan') {
          const plan = eventPayload<{ items?: PlanStep[] } | PlanStep[]>(data, 'plan')
          draft.plan = Array.isArray(plan) ? plan : plan?.items
        }
        if (eventName === 'done') completed = assistantFromDone(data, draft)
      }

      await streamMessage(activeThread, query, crypto.randomUUID(), intent, applyEvent)
      if (!completed) throw new Error('Stream ended before a complete message arrived')
      const finalMessages = [...nextMessages, completed]
      setMessages(finalMessages)
      stampHistory(activeThread, 'live')
    } catch {
      const demo = demoReply(query, intent)
      const localId = threadId?.startsWith('local-') ? threadId : `local-${crypto.randomUUID()}`
      const finalMessages = [...nextMessages, demo]
      setThreadId(localId)
      setMessages(finalMessages)
      saveLocalMessages(localId, finalMessages)
      stampHistory(localId, 'local')
      setNotice('Live assistant is unavailable. You’re viewing a curated demo response.')
    } finally {
      setLoading(false)
    }
  }

  const toggleCompare = (product: Product, checked: boolean) => {
    setSelected((current) =>
      checked
        ? current.some((item) => item.id === product.id)
          ? current
          : [...current, product].slice(-3)
        : current.filter((item) => item.id !== product.id),
    )
  }

  return (
    <section
      className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden"
      aria-label="Sports commerce assistant"
    >
      <header className="flex h-16 shrink-0 items-center gap-3 border-b border-zinc-200 px-4 dark:border-zinc-800 sm:px-6">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onOpenSidebar}
              aria-label={sidebarCollapsed ? 'Expand conversation history' : 'Open conversation history'}
              aria-pressed={!sidebarCollapsed}
            >
              {sidebarCollapsed ? <PanelLeft className="size-5" /> : <Menu className="size-5" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {sidebarCollapsed ? 'Show sidebar' : 'Hide or open sidebar'}
          </TooltipContent>
        </Tooltip>
        <div className="grid size-9 place-items-center rounded-xl bg-lime-400/15 text-lime-600 dark:text-lime-400">
          <Bot className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-bold">Stride Gear Strategist</h1>
          <p className="flex items-center gap-1 text-[11px] text-zinc-500">
            <span className="size-1.5 rounded-full bg-lime-500" /> Ready to scout
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={reset} aria-label="Reset conversation">
          <RotateCcw className="size-4" />
        </Button>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              onClick={onOpenCart}
              aria-label={cartCollapsed ? 'Expand shopping cart' : 'Open cart'}
              aria-pressed={!cartCollapsed}
            >
              {cartCollapsed ? <PanelRight className="size-5" /> : <ShoppingBag className="size-5" />}
              {cartCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 grid min-w-4 place-items-center rounded-full bg-lime-400 px-1 text-[10px] font-bold text-zinc-950">
                  {cartCount}
                </span>
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{cartCollapsed ? 'Show cart' : 'Hide or open cart'}</TooltipContent>
        </Tooltip>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        <div className="mx-auto max-w-4xl space-y-7 px-4 py-8 sm:px-7">
          <div>
            <p className="mb-3 flex items-center gap-2 text-xs font-semibold text-zinc-500">
              <Sparkles className="size-3.5 text-lime-500" /> Choose a play, or let Stride classify
              automatically
            </p>
            <ToggleGroup
              type="single"
              value={intent ?? ''}
              onValueChange={(value) => setIntent((value || undefined) as Intent | undefined)}
              aria-label="Shopping intent"
            >
              {intents.map(({ value, label, icon: Icon }) => (
                <ToggleGroupItem key={value} value={value} aria-label={label}>
                  <Icon className="size-3.5" /> {label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
          {notice && (
            <div
              role="alert"
              className="flex items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-800 dark:text-amber-200"
            >
              <span>{notice}</span>
              <Button variant="ghost" size="sm" onClick={() => submit()}>
                Retry
              </Button>
            </div>
          )}
          <div className="space-y-7" aria-live="polite">
            {hydrating ? (
              <div className="flex items-center gap-3 text-sm text-zinc-500">
                <LoaderCircle className="size-4 animate-spin text-lime-500" /> Loading conversation…
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={cn('flex gap-3', message.role === 'user' && 'justify-end')}
                >
                  {message.role === 'assistant' && (
                    <div className="mt-1 grid size-8 shrink-0 place-items-center rounded-xl bg-zinc-950 text-lime-400 dark:bg-zinc-800">
                      <Sparkles className="size-4" />
                    </div>
                  )}
                  <div
                    className={cn(
                      'min-w-0 max-w-[92%]',
                      message.role === 'user' &&
                        'rounded-2xl rounded-br-md bg-zinc-900 px-4 py-3 text-sm text-white dark:bg-zinc-100 dark:text-zinc-950',
                    )}
                  >
                    {message.role === 'assistant' && (
                      <p className="max-w-2xl text-sm leading-6 text-zinc-700 dark:text-zinc-200">
                        {message.content}
                      </p>
                    )}
                    {message.role === 'user' && message.content}
                    {message.recommendation && (
                      <div className="mt-4 rounded-xl border border-lime-500/30 bg-lime-400/10 px-4 py-3 text-sm font-semibold text-lime-800 dark:text-lime-300">
                        {message.recommendation}
                      </div>
                    )}
                    {message.plan && (
                      <ol className="mt-5 space-y-3">
                        {message.plan.map((step, index) => (
                          <li
                            key={`${step.title}-${index}`}
                            className="flex gap-3 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
                          >
                            <span className="grid size-7 shrink-0 place-items-center rounded-full bg-lime-400 text-xs font-black text-zinc-950">
                              {index + 1}
                            </span>
                            <div>
                              <p className="text-sm font-bold">{step.title}</p>
                              <p className="mt-1 text-xs text-zinc-500">{step.description}</p>
                            </div>
                          </li>
                        ))}
                      </ol>
                    )}
                    {message.products && (
                      <div className="mt-5 flex gap-4 overflow-x-auto pb-3">
                        {message.products.map((product) => (
                          <ProductCard
                            key={product.id}
                            product={product}
                            selected={selected.some((item) => item.id === product.id)}
                            onSelect={toggleCompare}
                          />
                        ))}
                      </div>
                    )}
                    {message.comparison && (
                      <div className="mt-5">
                        <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-500">
                          Head-to-head
                        </p>
                        <div className="flex gap-4 overflow-x-auto pb-3">
                          {message.comparison.map((product) => (
                            <ProductCard
                              key={product.id}
                              product={product}
                              selected={selected.some((item) => item.id === product.id)}
                              onSelect={toggleCompare}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                    {message.isDemo && (
                      <p className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                        Demo data
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex items-center gap-3 text-sm text-zinc-500">
                <LoaderCircle className="size-4 animate-spin text-lime-500" /> Scouting the best
                options…
              </div>
            )}
          </div>
          {selected.length > 1 && (
            <div className="rounded-2xl border border-lime-500/30 bg-lime-400/10 p-4">
              <p className="text-sm font-bold">{selected.length} products ready to compare</p>
              <p className="mt-1 text-xs text-zinc-500">
                {selected.map((item) => item.name).join(' · ')}
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 border-t border-zinc-200 bg-white/90 px-4 py-4 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/90 sm:px-7">
        <form
          onSubmit={submit}
          className="mx-auto flex max-w-4xl items-end gap-2 rounded-2xl border border-zinc-300 bg-zinc-50 p-2 shadow-lg shadow-black/5 focus-within:border-lime-500 dark:border-zinc-700 dark:bg-zinc-900"
        >
          <label className="sr-only" htmlFor="message">
            Message Stride
          </label>
          <textarea
            id="message"
            rows={1}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void submit()
              }
            }}
            placeholder="Ask about shoes, kits, equipment, or a training setup…"
            className="max-h-28 min-h-10 flex-1 resize-none bg-transparent px-3 py-2 text-sm outline-none placeholder:text-zinc-500"
          />
          <Button
            size="icon"
            type="submit"
            disabled={!content.trim() || loading || hydrating}
            aria-label="Send message"
          >
            <ArrowUp className="size-4" />
          </Button>
        </form>
        <p className="mx-auto mt-2 max-w-4xl text-center text-[10px] text-zinc-500">
          Stride can make mistakes. Verify fit, availability, and pricing with the retailer.
        </p>
      </div>
    </section>
  )
}
