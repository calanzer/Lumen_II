import type { PeriodStatus, PeriodSummary } from '@/lib/types'

export type DeadlineTone = 'done' | 'expired' | 'urgent' | 'soon' | 'ok'

/** Days left at or below which an unfinished reauthorization needs attention. */
export const URGENT_DAYS = 14
export const SOON_DAYS = 30

const FINISHED: ReadonlySet<PeriodStatus> = new Set(['exported', 'submitted'])

/** How worried to be about an authorization period: finished work is never urgent. */
export function deadlineTone(period: Pick<PeriodSummary, 'status' | 'days_until_end'>): DeadlineTone {
  if (FINISHED.has(period.status)) return 'done'
  if (period.days_until_end < 0) return 'expired'
  if (period.days_until_end <= URGENT_DAYS) return 'urgent'
  if (period.days_until_end <= SOON_DAYS) return 'soon'
  return 'ok'
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

export function describeDays(days: number): string {
  if (days < 0) return `Ended ${plural(-days, 'day')} ago`
  if (days === 0) return 'Ends today'
  return `${plural(days, 'day')} left`
}

export const STATUS_LABEL: Record<PeriodStatus, string> = {
  draft: 'Draft',
  in_progress: 'Reviewing',
  generated: 'Narrative ready',
  exported: 'Exported',
  submitted: 'Submitted',
}

export const formatDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
