import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import App from '@/App'
import { ThemeProvider } from '@/components/theme-provider'

vi.mock('@/api/conversation', () => ({
  createConversation: vi.fn().mockRejectedValue(new Error('offline')),
  streamMessage: vi.fn(),
}))

function renderApp() {
  return render(
    <ThemeProvider>
      <App />
    </ThemeProvider>,
  )
}

describe('sports commerce chat', () => {
  it('defaults to dark and switches/persists theme', async () => {
    const user = userEvent.setup()
    renderApp()
    await waitFor(() => expect(document.documentElement).toHaveClass('dark'))
    await user.click(screen.getByRole('button', { name: 'Open conversation history' }))
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: /profile and theme/i }))
    await user.click(screen.getByRole('menuitem', { name: /light/i }))
    expect(document.documentElement).not.toHaveClass('dark')
    expect(localStorage.getItem('stride:theme')).toBe('light')
  })

  it('renders, selects an intent, submits, and shows bounded fallback products', async () => {
    const user = userEvent.setup()
    renderApp()
    expect(screen.getByRole('heading', { name: /stride gear strategist/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Open conversation history' }))
    expect(within(screen.getByRole('dialog')).getByText(/no conversations yet/i)).toBeInTheDocument()
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Close panel' }))
    await user.click(screen.getByRole('radio', { name: 'Compare' }))
    expect(screen.getByRole('radio', { name: 'Compare' })).toHaveAttribute('data-state', 'on')
    await user.type(screen.getByLabelText('Message Stride'), 'daily running shoes')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/curated demo response/i)
    expect(screen.getByText('Clifton 9')).toBeInTheDocument()
    expect(screen.getAllByText(/demo data/i)).toHaveLength(1)
    await user.click(screen.getByRole('button', { name: 'Open conversation history' }))
    expect(within(screen.getByRole('dialog')).getByText(/daily running shoes/i)).toBeInTheDocument()
  })

  it('selects products for comparison and manages a persistent cart', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.type(screen.getByLabelText('Message Stride'), 'comfortable trainers')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText('Pegasus 41')
    await user.click(screen.getByLabelText('Compare Pegasus 41'))
    await user.click(screen.getByLabelText('Compare Clifton 9'))
    expect(screen.getByText(/2 products ready to compare/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Add Clifton 9 to cart' }))
    await user.click(screen.getByRole('button', { name: 'Open cart' }))
    const cart = screen.getByRole('dialog')
    expect(within(cart).getByText('Cart')).toBeInTheDocument()
    expect(within(cart).getByText('(1)')).toBeInTheDocument()
    await user.click(within(cart).getByRole('button', { name: 'Increase Clifton 9 quantity' }))
    expect(within(cart).getByLabelText('Quantity 2')).toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem('stride:cart') ?? '{}')).toMatchObject({ version: 1 })
    await user.click(within(cart).getByRole('button', { name: 'Mock checkout' }))
    expect(screen.getByRole('heading', { name: /ready for the podium/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Confirm mock order' }))
    expect(screen.getByText(/order simulation complete/i)).toBeInTheDocument()
  })

  it('collapses and expands desktop side panels', async () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query.includes('1280px'),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
    const user = userEvent.setup()
    renderApp()
    expect(screen.getByLabelText('Collapse conversation history')).toBeInTheDocument()
    expect(screen.getByLabelText('Collapse shopping cart')).toBeInTheDocument()
    await user.click(screen.getByLabelText('Collapse conversation history'))
    expect(screen.getByLabelText('Expand conversation history')).toBeInTheDocument()
    await user.click(screen.getByLabelText('Expand conversation history'))
    expect(screen.getByLabelText('Collapse conversation history')).toBeInTheDocument()
    await user.click(screen.getByLabelText('Collapse shopping cart'))
    expect(screen.getByLabelText('Expand shopping cart')).toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem('stride:layout:v1') ?? '{}')).toMatchObject({
      sidebarVisible: true,
      cartVisible: false,
    })
  })
})
