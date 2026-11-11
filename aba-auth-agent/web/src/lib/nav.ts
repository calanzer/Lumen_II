import { Download, FileSearch, FileText, LayoutTemplate, Upload, Users } from 'lucide-react'

export const NAV = [
  { to: '/import', label: 'Import', icon: Upload },
  { to: '/clients', label: 'Clients', icon: Users },
  { to: '/review', label: 'Review data', icon: FileSearch },
  { to: '/generate', label: 'Generate', icon: FileText },
  { to: '/export', label: 'Export', icon: Download },
  { to: '/templates', label: 'Templates', icon: LayoutTemplate },
] as const

/** The sidebar links that really mean "this step for the period I'm working on". */
const PERIOD_STEPS = ['/review', '/generate', '/export']

/** Whether a sidebar link is the current page: `/review` also covers `/periods/<id>/review`. */
export function isNavActive(to: string, pathname: string): boolean {
  if (pathname === to || pathname.startsWith(`${to}/`)) return true
  return PERIOD_STEPS.includes(to) && /^\/periods\/[^/]+\//.test(pathname) && pathname.endsWith(to)
}

/** Screens that need the room for side-by-side editing. */
export const isWidePage = (pathname: string) => pathname.startsWith('/periods/') || pathname === '/templates'
