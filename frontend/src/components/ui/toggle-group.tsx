import * as ToggleGroupPrimitive from '@radix-ui/react-toggle-group'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

export function ToggleGroup({
  className,
  ...props
}: ComponentProps<typeof ToggleGroupPrimitive.Root>) {
  return <ToggleGroupPrimitive.Root className={cn('flex flex-wrap gap-2', className)} {...props} />
}

export function ToggleGroupItem({
  className,
  ...props
}: ComponentProps<typeof ToggleGroupPrimitive.Item>) {
  return (
    <ToggleGroupPrimitive.Item
      className={cn(
        'inline-flex h-9 items-center gap-2 rounded-full border border-zinc-300 px-3 text-xs font-semibold text-zinc-600 transition-colors hover:bg-zinc-100 data-[state=on]:border-lime-500 data-[state=on]:bg-lime-400/15 data-[state=on]:text-zinc-950 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 dark:data-[state=on]:text-lime-300',
        className,
      )}
      {...props}
    />
  )
}
