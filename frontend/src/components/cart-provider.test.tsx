import { renderHook, act } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CartProvider, useCart } from '@/components/cart-provider'
import { demoProducts } from '@/data/demo'

describe('cart provider', () => {
  it('persists versioned cart state and bounds quantities', () => {
    const { result } = renderHook(() => useCart(), {
      wrapper: ({ children }) => <CartProvider>{children}</CartProvider>,
    })

    act(() => result.current.add(demoProducts[0]))
    act(() => result.current.setQuantity(demoProducts[0].id, 99))
    expect(result.current.lines[0]?.quantity).toBe(20)
    expect(result.current.subtotal).toBe(demoProducts[0].price * 20)

    const saved = JSON.parse(localStorage.getItem('stride:cart') ?? '{}') as {
      version: number
      lines: unknown[]
    }
    expect(saved.version).toBe(1)
    expect(saved.lines).toHaveLength(1)

    act(() => result.current.clear())
    expect(result.current.count).toBe(0)
  })
})
