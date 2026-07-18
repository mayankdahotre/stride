import { useState } from 'react'
import { CartPanel } from '@/components/cart-panel'
import { CartProvider, useCart } from '@/components/cart-provider'
import { ChatPanel } from '@/components/chat-panel'
import { Sidebar } from '@/components/sidebar'
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet'
import { TooltipProvider } from '@/components/ui/tooltip'
import { loadHistory, upsertHistory } from '@/lib/conversation-history'
import { cn } from '@/lib/utils'
import type { ConversationSummary } from '@/types'

const LAYOUT_KEY = 'stride:layout:v1'

function loadLayout() {
  try {
    const saved = JSON.parse(localStorage.getItem(LAYOUT_KEY) ?? '{}') as {
      sidebarVisible?: boolean
      cartVisible?: boolean
    }
    return {
      sidebarVisible: saved.sidebarVisible ?? true,
      cartVisible: saved.cartVisible ?? true,
    }
  } catch {
    return { sidebarVisible: true, cartVisible: true }
  }
}

function saveLayout(sidebarVisible: boolean, cartVisible: boolean) {
  localStorage.setItem(LAYOUT_KEY, JSON.stringify({ sidebarVisible, cartVisible }))
}

function isDesktopLayout() {
  return window.matchMedia('(min-width: 1280px)').matches
}

function AppShell() {
  const { count } = useCart()
  const initialLayout = loadLayout()
  const [sidebarSheetOpen, setSidebarSheetOpen] = useState(false)
  const [cartSheetOpen, setCartSheetOpen] = useState(false)
  const [sidebarVisible, setSidebarVisible] = useState(initialLayout.sidebarVisible)
  const [cartVisible, setCartVisible] = useState(initialLayout.cartVisible)
  const [conversations, setConversations] = useState(() => loadHistory())
  const [activeId, setActiveId] = useState<string | null>(null)
  const [chatKey, setChatKey] = useState(0)

  const persistLayout = (nextSidebar: boolean, nextCart: boolean) => {
    setSidebarVisible(nextSidebar)
    setCartVisible(nextCart)
    saveLayout(nextSidebar, nextCart)
  }

  const startNewChat = () => {
    setActiveId(null)
    setChatKey((value) => value + 1)
    setSidebarSheetOpen(false)
  }

  const selectConversation = (id: string) => {
    if (id === activeId) {
      setSidebarSheetOpen(false)
      return
    }
    setActiveId(id)
    setSidebarSheetOpen(false)
  }

  const handleUpsert = (summary: ConversationSummary) => {
    setConversations((current) => upsertHistory(current, summary))
    setActiveId(summary.id)
  }

  const handleSidebarButton = () => {
    if (isDesktopLayout()) {
      persistLayout(!sidebarVisible, cartVisible)
      return
    }
    setSidebarSheetOpen(true)
  }

  const handleCartButton = () => {
    if (isDesktopLayout()) {
      persistLayout(sidebarVisible, !cartVisible)
      return
    }
    setCartSheetOpen(true)
  }

  return (
    <div className="h-dvh overflow-hidden bg-white text-zinc-950 dark:bg-zinc-950 dark:text-zinc-50">
      <div className="flex h-full min-h-0">
        <aside
          className={cn(
            'hidden min-h-0 shrink-0 overflow-hidden border-zinc-200 bg-zinc-50 transition-[width,opacity] duration-200 dark:border-zinc-800 dark:bg-zinc-950 xl:block',
            sidebarVisible ? 'w-64 border-r opacity-100' : 'w-0 border-0 opacity-0',
          )}
          aria-hidden={!sidebarVisible}
        >
          <div className="h-full w-64 p-5">
            <Sidebar
              conversations={conversations}
              activeId={activeId}
              onNewChat={startNewChat}
              onSelect={selectConversation}
              onCollapse={() => persistLayout(false, cartVisible)}
            />
          </div>
        </aside>

        <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
          <ChatPanel
            key={chatKey}
            conversationId={activeId}
            cartCount={count}
            sidebarCollapsed={!sidebarVisible}
            cartCollapsed={!cartVisible}
            onOpenSidebar={handleSidebarButton}
            onOpenCart={handleCartButton}
            onConversationUpsert={handleUpsert}
            onResetConversation={startNewChat}
          />
        </main>

        <aside
          className={cn(
            'hidden min-h-0 shrink-0 overflow-hidden border-zinc-200 bg-zinc-50 transition-[width,opacity] duration-200 dark:border-zinc-800 dark:bg-zinc-950 xl:block',
            cartVisible ? 'w-[312px] border-l opacity-100' : 'w-0 border-0 opacity-0',
          )}
          aria-hidden={!cartVisible}
        >
          <div className="h-full w-[312px] p-5">
            <CartPanel onCollapse={() => persistLayout(sidebarVisible, false)} />
          </div>
        </aside>
      </div>

      <Sheet open={sidebarSheetOpen} onOpenChange={setSidebarSheetOpen}>
        <SheetContent side="left">
          <SheetTitle className="sr-only">Conversation history</SheetTitle>
          <Sidebar
            conversations={conversations}
            activeId={activeId}
            onNewChat={startNewChat}
            onSelect={selectConversation}
          />
        </SheetContent>
      </Sheet>
      <Sheet open={cartSheetOpen} onOpenChange={setCartSheetOpen}>
        <SheetContent side="right">
          <SheetTitle className="sr-only">Shopping cart</SheetTitle>
          <CartPanel />
        </SheetContent>
      </Sheet>
    </div>
  )
}

export default function App() {
  return (
    <TooltipProvider>
      <CartProvider>
        <AppShell />
      </CartProvider>
    </TooltipProvider>
  )
}
