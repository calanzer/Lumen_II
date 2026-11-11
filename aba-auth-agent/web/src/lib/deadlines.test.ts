import { describe, expect, it } from 'vitest'

import { deadlineTone, describeDays, formatDate, SOON_DAYS, URGENT_DAYS } from '@/lib/deadlines'

describe('deadlineTone', () => {
  it('is expired once the authorization has ended and the work is not finished', () => {
    expect(deadlineTone({ status: 'in_progress', days_until_end: -1 })).toBe('expired')
    expect(deadlineTone({ status: 'draft', days_until_end: -90 })).toBe('expired')
  })

  it('is urgent up to two weeks out, soon up to a month, then ok', () => {
    expect(deadlineTone({ status: 'draft', days_until_end: 0 })).toBe('urgent')
    expect(deadlineTone({ status: 'draft', days_until_end: URGENT_DAYS })).toBe('urgent')
    expect(deadlineTone({ status: 'draft', days_until_end: URGENT_DAYS + 1 })).toBe('soon')
    expect(deadlineTone({ status: 'draft', days_until_end: SOON_DAYS })).toBe('soon')
    expect(deadlineTone({ status: 'draft', days_until_end: SOON_DAYS + 1 })).toBe('ok')
  })

  it('never alarms about work that is already exported or submitted', () => {
    expect(deadlineTone({ status: 'exported', days_until_end: -50 })).toBe('done')
    expect(deadlineTone({ status: 'submitted', days_until_end: 3 })).toBe('done')
  })

  it('treats a generated narrative as still unfinished', () => {
    expect(deadlineTone({ status: 'generated', days_until_end: 5 })).toBe('urgent')
  })
})

describe('describeDays', () => {
  it('speaks plainly with correct plurals', () => {
    expect(describeDays(71)).toBe('71 days left')
    expect(describeDays(1)).toBe('1 day left')
    expect(describeDays(0)).toBe('Ends today')
    expect(describeDays(-1)).toBe('Ended 1 day ago')
    expect(describeDays(-12)).toBe('Ended 12 days ago')
  })
})

describe('formatDate', () => {
  it('shows an ISO date without sliding a day with the time zone', () => {
    expect(formatDate('2026-06-30')).toMatch(/Jun 30, 2026/)
    expect(formatDate('2026-01-01')).toMatch(/Jan 1, 2026/)
  })
})
