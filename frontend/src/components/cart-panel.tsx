import { CheckCircle2, Minus, PanelRightClose, Plus, ShoppingBag, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useCart } from '@/components/cart-provider'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { formatPrice } from '@/lib/utils'

export function CartPanel({ onCollapse }: { onCollapse?: () => void }) {
  const { lines, count, subtotal, setQuantity, remove, clear } = useCart()
  const [checkoutOpen, setCheckoutOpen] = useState(false)
  const [confirmed, setConfirmed] = useState(false)

  return (
    <aside aria-label="Shopping cart" className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-lime-600 dark:text-lime-400">Your locker</p>
          <h2 className="mt-1 text-lg font-bold">Cart <span className="text-zinc-400">({count})</span></h2>
        </div>
        <div className="flex items-center gap-1">
          {lines.length > 0 && <Button variant="ghost" size="sm" onClick={clear}>Clear</Button>}
          {onCollapse && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="hidden xl:inline-flex"
                  onClick={onCollapse}
                  aria-label="Collapse shopping cart"
                >
                  <PanelRightClose className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Collapse cart</TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>
      <Separator className="my-5" />
      {lines.length === 0 ? (
        <div className="grid flex-1 place-content-center px-4 text-center">
          <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-zinc-100 text-zinc-400 dark:bg-zinc-900">
            <ShoppingBag className="size-6" />
          </div>
          <h3 className="mt-4 font-semibold">Your cart is ready</h3>
          <p className="mt-1 max-w-48 text-sm text-zinc-500">Add a recommended product to keep it close.</p>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1">
          <div className="space-y-4 pr-2">
            {lines.map(({ product, quantity }) => (
              <div key={product.id} className="flex gap-3">
                <div className="size-14 shrink-0 overflow-hidden rounded-xl bg-zinc-100 dark:bg-zinc-800">
                  {product.image && <img src={product.image} alt="" className="size-full object-cover" />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{product.name}</p>
                  <p className="text-xs font-medium text-zinc-500">{formatPrice(product.price, product.currency)}</p>
                  <div className="mt-2 flex items-center gap-1">
                    <Button variant="outline" size="icon" className="size-7" onClick={() => setQuantity(product.id, quantity - 1)} aria-label={`Decrease ${product.name} quantity`}><Minus className="size-3" /></Button>
                    <span className="w-7 text-center text-xs font-semibold" aria-label={`Quantity ${quantity}`}>{quantity}</span>
                    <Button variant="outline" size="icon" className="size-7" onClick={() => setQuantity(product.id, quantity + 1)} aria-label={`Increase ${product.name} quantity`}><Plus className="size-3" /></Button>
                    <Button variant="ghost" size="icon" className="ml-auto size-7 text-zinc-400" onClick={() => remove(product.id)} aria-label={`Remove ${product.name}`}><Trash2 className="size-3.5" /></Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="mt-5 border-t border-zinc-200 pt-5 dark:border-zinc-800">
        <div className="mb-4 flex justify-between"><span className="text-sm text-zinc-500">Subtotal</span><strong>{formatPrice(subtotal)}</strong></div>
        <Button className="w-full" disabled={!lines.length} onClick={() => { setConfirmed(false); setCheckoutOpen(true) }}>Mock checkout</Button>
        <p className="mt-2 text-center text-[11px] text-zinc-500">Demo only · no payment collected</p>
      </div>
      <Dialog open={checkoutOpen} onOpenChange={setCheckoutOpen}>
        <DialogContent>
          {confirmed ? (
            <div className="py-5 text-center">
              <CheckCircle2 className="mx-auto size-12 text-lime-500" />
              <DialogTitle className="mt-4">Order simulation complete</DialogTitle>
              <DialogDescription>Your gear is not actually ordered—this confirms the checkout flow works.</DialogDescription>
              <Button className="mt-5" onClick={() => setCheckoutOpen(false)}>Done</Button>
            </div>
          ) : (
            <>
              <DialogTitle>Ready for the podium?</DialogTitle>
              <DialogDescription>Confirm this mock order for {count} item{count === 1 ? '' : 's'} totaling {formatPrice(subtotal)}.</DialogDescription>
              <Button className="mt-6 w-full" onClick={() => setConfirmed(true)}>Confirm mock order</Button>
            </>
          )}
        </DialogContent>
      </Dialog>
    </aside>
  )
}
