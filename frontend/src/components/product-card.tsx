import { Check, ImageOff, Plus, Star } from 'lucide-react'
import { useState } from 'react'
import { useCart } from '@/components/cart-provider'
import { Button } from '@/components/ui/button'
import { cn, formatPrice } from '@/lib/utils'
import type { Product } from '@/types'

export function ProductCard({
  product,
  selected,
  onSelect,
}: {
  product: Product
  selected?: boolean
  onSelect?: (product: Product, selected: boolean) => void
}) {
  const { add } = useCart()
  const [failedImage, setFailedImage] = useState(false)
  return (
    <article className="group min-w-[238px] max-w-[280px] overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="relative h-36 overflow-hidden bg-zinc-100 dark:bg-zinc-800">
        {product.image && !failedImage ? (
          <img
            src={product.image}
            alt={product.name}
            loading="lazy"
            onError={() => setFailedImage(true)}
            className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex size-full items-center justify-center text-zinc-400">
            <ImageOff className="size-8" aria-hidden="true" />
            <span className="sr-only">Image unavailable</span>
          </div>
        )}
        {onSelect && (
          <label className="absolute left-3 top-3 flex cursor-pointer items-center gap-2 rounded-full bg-zinc-950/85 px-2.5 py-1.5 text-xs font-medium text-white backdrop-blur">
            <input
              className="sr-only"
              type="checkbox"
              checked={selected}
              onChange={(event) => onSelect(product, event.target.checked)}
              aria-label={`Compare ${product.name}`}
            />
            <span className={cn('grid size-4 place-items-center rounded border border-white/50', selected && 'border-lime-400 bg-lime-400 text-zinc-950')}>
              {selected && <Check className="size-3" />}
            </span>
            Compare
          </label>
        )}
      </div>
      <div className="space-y-3 p-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-lime-600 dark:text-lime-400">
            {product.brand ?? product.merchant ?? 'Stride pick'}
          </p>
          <h3 className="mt-1 font-bold text-zinc-950 dark:text-zinc-50">{product.name}</h3>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
            {product.description}
          </p>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-bold">{formatPrice(product.price, product.currency)}</p>
            {product.rating && (
              <p className="flex items-center gap-1 text-xs text-zinc-500">
                <Star className="size-3 fill-lime-400 text-lime-400" /> {product.rating}
                {product.reviews ? ` (${product.reviews})` : ''}
              </p>
            )}
          </div>
          <Button size="sm" onClick={() => add(product)} aria-label={`Add ${product.name} to cart`}>
            <Plus className="size-3.5" /> Add
          </Button>
        </div>
      </div>
    </article>
  )
}
