import { Check, ChevronDown, MessageSquarePlus, Moon, PanelLeftClose, Plus, Sun, SunMoon } from 'lucide-react'
import { useTheme, type Theme } from '@/components/theme-provider'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { formatRelativeTime } from '@/lib/conversation-history'
import { cn } from '@/lib/utils'
import type { ConversationSummary } from '@/types'

const themes: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: SunMoon },
]

export function Sidebar({
  conversations,
  activeId,
  onNewChat,
  onSelect,
  onCollapse,
}: {
  conversations: ConversationSummary[]
  activeId?: string | null
  onNewChat: () => void
  onSelect: (id: string) => void
  onCollapse?: () => void
}) {
  const { theme, setTheme } = useTheme()

  return (
    <nav aria-label="Conversation history" className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl bg-lime-400 font-black text-zinc-950">S</div>
        <div className="min-w-0 flex-1">
          <p className="font-black tracking-tight">STRIDE</p>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
            Sport intelligence
          </p>
        </div>
        {onCollapse && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="hidden xl:inline-flex"
                onClick={onCollapse}
                aria-label="Collapse conversation history"
              >
                <PanelLeftClose className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Collapse sidebar</TooltipContent>
          </Tooltip>
        )}
      </div>
      <Button className="mt-7 w-full justify-start" onClick={onNewChat}>
        <Plus className="size-4" /> New conversation
      </Button>
      <div className="mt-7 flex items-center justify-between px-1">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-500">Recent</p>
      </div>
      <div className="mt-2 min-h-0 flex-1 space-y-1 overflow-y-auto overscroll-contain pr-1">
        {conversations.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-300 px-3 py-6 text-center dark:border-zinc-700">
            <MessageSquarePlus className="mx-auto size-5 text-zinc-400" />
            <p className="mt-2 text-sm font-medium">No conversations yet</p>
            <p className="mt-1 text-xs text-zinc-500">Send a message and it will appear here.</p>
          </div>
        ) : (
          conversations.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              className={cn(
                'flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-900',
                activeId === item.id && 'bg-zinc-100 font-semibold dark:bg-zinc-900',
              )}
            >
              <span className="truncate">{item.title}</span>
              <span className="ml-2 shrink-0 text-[10px] text-zinc-500">
                {formatRelativeTime(item.updatedAt)}
              </span>
            </button>
          ))
        )}
      </div>
      <div className="mt-auto shrink-0 pt-4">
        <Separator className="mb-4" />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className="flex w-full items-center gap-3 rounded-xl p-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-900"
              aria-label="Open profile and theme menu"
            >
              <div className="grid size-9 place-items-center rounded-full bg-gradient-to-br from-lime-300 to-emerald-500 text-xs font-black text-zinc-950">
                MD
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">Mayank</p>
                <p className="text-xs text-zinc-500">Athlete profile</p>
              </div>
              <ChevronDown className="size-4 text-zinc-500" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            {themes.map(({ value, label, icon: Icon }) => (
              <DropdownMenuItem key={value} onSelect={() => setTheme(value)}>
                <Icon className="size-4" /> {label}
                {theme === value && <Check className="ml-auto size-4 text-lime-500" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </nav>
  )
}
