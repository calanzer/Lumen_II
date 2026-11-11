import { LogOut, Menu } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router'

import { useAuth } from '@/auth/useAuth'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { isNavActive, isWidePage, NAV } from '@/lib/nav'
import { cn } from '@/lib/utils'

function Brand() {
  return (
    <div className="flex items-center gap-2 font-semibold tracking-tight">
      <img src="/favicon.svg" alt="" className="size-7" />
      Lumen ABA
    </div>
  )
}

function UserMenu({ compact = false }: { compact?: boolean }) {
  const { user, logout } = useAuth()
  if (!user) return null
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className={cn('justify-start', compact ? 'px-2' : 'w-full')}>
          <span className="flex size-7 items-center justify-center rounded-full bg-accent text-xs font-medium text-accent-foreground">
            {user.name.slice(0, 1)}
          </span>
          {!compact && <span className="truncate">{user.name}</span>}
          {!compact && user.local && (
            <Badge variant="outline" className="ml-auto">
              Local
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuLabel>{user.name}</DropdownMenuLabel>
        {user.local ? (
          <p className="px-2 pb-2 text-xs text-muted-foreground">Sign-in is skipped because this is running on your computer.</p>
        ) : (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => void logout()}>
              <LogOut /> Sign out
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function AppShell() {
  const { pathname } = useLocation()
  return (
    <div className="min-h-svh md:grid md:grid-cols-[15rem_1fr]">
      {/* Wide screens: fixed sidebar */}
      <aside className="hidden border-r bg-sidebar p-3 md:flex md:flex-col md:gap-4">
        <div className="px-2 pt-1">
          <Brand />
        </div>
        <nav aria-label="Main" className="flex flex-1 flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              aria-current={isNavActive(to, pathname) ? 'page' : undefined}
              className={cn(
                'flex items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-foreground transition-colors hover:bg-sidebar-accent',
                isNavActive(to, pathname) && 'bg-sidebar-accent font-medium text-sidebar-accent-foreground',
              )}
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <UserMenu />
      </aside>

      {/* Narrow screens: top bar with the same links in a menu */}
      <header className="flex items-center justify-between border-b bg-sidebar px-4 py-2 md:hidden">
        <Brand />
        <div className="flex items-center gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open menu">
                <Menu />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {NAV.map(({ to, label, icon: Icon }) => (
                <DropdownMenuItem key={to} asChild>
                  <NavLink to={to}>
                    <Icon /> {label}
                  </NavLink>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <UserMenu compact />
        </div>
      </header>

      <main className="px-4 py-8 md:px-10">
        <div className={cn('mx-auto w-full', isWidePage(pathname) ? 'max-w-6xl' : 'max-w-3xl')}>
          <Outlet />
        </div>
      </main>
    </div>
  )
}
