import type { TemplateDraft, TemplateSection } from '@/lib/types'

/** A section row being edited. The id keeps a row's identity as rows are moved, added and removed. */
export interface Row extends TemplateSection {
  id: number
}

let nextId = 1
export const newRow = (section: Partial<TemplateSection> = {}): Row => ({
  id: nextId++,
  title: section.title ?? '',
  guidance: section.guidance ?? '',
})

export const rowsFrom = (sections: TemplateSection[]): Row[] => sections.map((section) => newRow(section))

/** Moves a row up (-1) or down (+1); a row at the end stays where it is. */
export function moveRow(rows: Row[], index: number, by: -1 | 1): Row[] {
  const target = index + by
  if (target < 0 || target >= rows.length) return rows
  const next = [...rows]
  ;[next[index], next[target]] = [next[target], next[index]]
  return next
}

export const MIN_SECTIONS = 2

/** What stops this draft from being saved, in words; null when it's fine. */
export function templateProblem(name: string, rows: Row[]): string | null {
  if (!name.trim()) return 'Give the template a name.'
  if (rows.filter((row) => row.title.trim()).length < MIN_SECTIONS) return 'A template needs at least two sections.'
  return null
}

export const toDraft = (rows: Row[], style_notes: string, source_filename: string | null): TemplateDraft => ({
  source_filename,
  style_notes: style_notes.trim(),
  sections: rows.filter((row) => row.title.trim()).map(({ title, guidance }) => ({ title: title.trim(), guidance: guidance.trim() })),
})
