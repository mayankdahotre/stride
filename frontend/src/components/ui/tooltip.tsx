import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

export const TooltipProvider = TooltipPrimitive.Provider
export const Tooltip = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export function TooltipContent({
  className,
  ...props
}: ComponentProps<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={6}
        className={cn('z-50 rounded-lg bg-zinc-950 px-2.5 py-1.5 text-xs text-white shadow-xl dark:bg-zinc-100 dark:text-zinc-950', className)}
        {...props}
      />
    </TooltipPrimitive.Portal>
  )
}
