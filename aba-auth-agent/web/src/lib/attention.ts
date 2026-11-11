import type { ImportResult } from '@/lib/types'

/** The lists the BCBA should look at, as tabs so a long list doesn't push the others off screen. */
export function attentionLists(result: ImportResult): { key: string; label: string; items: string[] }[] {
  return [
    { key: 'missing', label: 'Missing from the report', items: result.missing },
    { key: 'warnings', label: 'Warnings', items: result.warnings },
    { key: 'flags', label: 'Draft flags', items: result.draft?.flags ?? [] },
    { key: 'numbers', label: 'Numbers to verify', items: result.discrepancies ?? [] },
  ]
}
