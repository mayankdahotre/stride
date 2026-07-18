import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from 'react'
import type { Product } from '@/types'

export interface CartLine {
  product: Product
  quantity: number
}

interface CartState {
  lines: CartLine[]
}

type CartAction =
  | { type: 'add'; product: Product }
  | { type: 'quantity'; id: string; quantity: number }
  | { type: 'remove'; id: string }
  | { type: 'clear' }

interface CartContextValue extends CartState {
  add: (product: Product) => void
  setQuantity: (id: string, quantity: number) => void
  remove: (id: string) => void
  clear: () => void
  count: number
  subtotal: number
}

const STORAGE_KEY = 'stride:cart'
const STORAGE_VERSION = 1
const MAX_QUANTITY = 20
const CartContext = createContext<CartContextValue | null>(null)

function boundedQuantity(quantity: number) {
  return Math.max(1, Math.min(MAX_QUANTITY, Math.floor(quantity) || 1))
}

function reducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case 'add': {
      const existing = state.lines.find((line) => line.product.id === action.product.id)
      if (existing) {
        return {
          lines: state.lines.map((line) =>
            line.product.id === action.product.id
              ? { ...line, quantity: boundedQuantity(line.quantity + 1) }
              : line,
          ),
        }
      }
      return { lines: [...state.lines, { product: action.product, quantity: 1 }] }
    }
    case 'quantity':
      return {
        lines: state.lines.map((line) =>
          line.product.id === action.id
            ? { ...line, quantity: boundedQuantity(action.quantity) }
            : line,
        ),
      }
    case 'remove':
      return { lines: state.lines.filter((line) => line.product.id !== action.id) }
    case 'clear':
      return { lines: [] }
  }
}

function initialState(): CartState {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null') as {
      version?: number
      lines?: CartLine[]
    } | null
    if (saved?.version === STORAGE_VERSION && Array.isArray(saved.lines)) {
      return {
        lines: saved.lines
          .filter((line) => line?.product?.id && Number.isFinite(line.product.price))
          .map((line) => ({ product: line.product, quantity: boundedQuantity(line.quantity) })),
      }
    }
  } catch {
    // Ignore invalid persisted state.
  }
  return { lines: [] }
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, initialState)
  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ version: STORAGE_VERSION, lines: state.lines }),
    )
  }, [state.lines])

  const value = useMemo<CartContextValue>(
    () => ({
      ...state,
      add: (product) => dispatch({ type: 'add', product }),
      setQuantity: (id, quantity) => dispatch({ type: 'quantity', id, quantity }),
      remove: (id) => dispatch({ type: 'remove', id }),
      clear: () => dispatch({ type: 'clear' }),
      count: state.lines.reduce((sum, line) => sum + line.quantity, 0),
      subtotal: state.lines.reduce(
        (sum, line) => sum + line.product.price * line.quantity,
        0,
      ),
    }),
    [state],
  )
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart() {
  const context = useContext(CartContext)
  if (!context) throw new Error('useCart must be used inside CartProvider')
  return context
}
