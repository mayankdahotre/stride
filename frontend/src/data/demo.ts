import type { ChatMessage, Intent, Product } from '@/types'

export const demoProducts: Product[] = [
  {
    id: 'nike-pegasus-41',
    name: 'Pegasus 41',
    brand: 'Nike',
    description: 'Responsive everyday road runner with breathable engineered mesh.',
    category: 'Road running',
    image: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=700&q=80',
    price: 140,
    rating: 4.7,
    reviews: 862,
    merchant: 'Nike',
  },
  {
    id: 'hoka-clifton-9',
    name: 'Clifton 9',
    brand: 'HOKA',
    description: 'Plush, lightweight cushioning for daily miles and recovery runs.',
    category: 'Road running',
    image: 'https://images.unsplash.com/photo-1608231387042-66d1773070a5?auto=format&fit=crop&w=700&q=80',
    price: 145,
    rating: 4.8,
    reviews: 1243,
    merchant: 'HOKA',
  },
  {
    id: 'asics-novablast-5',
    name: 'Novablast 5',
    brand: 'ASICS',
    description: 'Energetic foam and a stable platform for uptempo daily training.',
    category: 'Road running',
    image: 'https://images.unsplash.com/photo-1552346154-21d32810aba3?auto=format&fit=crop&w=700&q=80',
    price: 150,
    rating: 4.6,
    reviews: 531,
    merchant: 'ASICS',
  },
]

export const welcomeMessage: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content:
    "I'm your sports gear strategist. Tell me your sport, goals, fit preferences, and budget—I’ll narrow the field without the sponsored noise.",
  createdAt: new Date().toISOString(),
}

export function demoReply(query: string, intent?: Intent): ChatMessage {
  const mode = intent ?? 'recommend'
  const intro: Record<Intent, string> = {
    search: `I found three strong matches for “${query}”. They balance performance, durability, and current value.`,
    compare: 'Here’s a focused comparison. The Clifton is softer; the Pegasus feels more versatile; the Novablast has the liveliest ride.',
    recommend: 'For most daily runners, I’d start with the HOKA Clifton 9. It offers the best comfort-to-weight balance in this group.',
    plan: 'I built a simple gear plan that prioritizes fit first, then rotates in performance pieces as your training volume grows.',
  }
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: intro[mode],
    createdAt: new Date().toISOString(),
    products: mode === 'search' || mode === 'recommend' ? demoProducts : undefined,
    comparison: mode === 'compare' ? demoProducts : undefined,
    recommendation: mode === 'recommend' ? 'Best overall: HOKA Clifton 9' : undefined,
    plan:
      mode === 'plan'
        ? [
            { title: 'Dial in the daily trainer', description: 'Try both sizes late in the day.', status: 'active' },
            { title: 'Add a speed-day shoe', description: 'After 3–4 consistent weeks.', status: 'upcoming' },
            { title: 'Review wear at 300 miles', description: 'Check outsole and midsole compression.', status: 'upcoming' },
          ]
        : undefined,
    isDemo: true,
  }
}
