import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { ImportResultView } from '@/components/import/ImportResultView'
import { attentionLists } from '@/lib/attention'
import { result } from '@/test/fixtures'

const show = (overrides = {}) =>
  render(
    <MemoryRouter>
      <ImportResultView result={result(overrides)} filename="report.docx" onAnother={vi.fn()} />
    </MemoryRouter>,
  )

describe('ImportResultView', () => {
  it('leads straight on to reviewing the imported data and to the draft', () => {
    show({ period_id: 'p9' })
    expect(screen.getByRole('link', { name: 'Review the data' })).toHaveAttribute('href', '/periods/p9/review')
    expect(screen.getByRole('link', { name: 'Open the draft' })).toHaveAttribute('href', '/periods/p9/generate')
  })

  it('offers no draft link when the draft failed', () => {
    show({ draft: null, draft_error: 'model overloaded' })
    expect(screen.getByRole('link', { name: 'Review the data' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open the draft' })).not.toBeInTheDocument()
  })

  it('says what was imported and the decisions made on the BCBA\'s behalf', () => {
    show()
    expect(screen.getByText('Imported report.docx')).toBeInTheDocument()
    expect(screen.getByText(/HB-2025-0311 · Aetna · Jan 1, 2026 to Jun 30, 2026/)).toBeInTheDocument()
    expect(screen.getByText('New client created: HB-2025-0311.')).toBeInTheDocument()
  })

  it('shows the headline numbers', () => {
    show({ completeness: 0.82, missing: ['Authorization period start date', 'Authorization period end date'] })
    expect(screen.getByText('82%')).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Missing required' })).toHaveTextContent('2')
    expect(screen.getByRole('group', { name: 'Draft flags' })).toHaveTextContent('2')
  })

  it('opens on the first list that has something in it', () => {
    show({ missing: [], warnings: ['A warning'] })
    expect(screen.getByRole('tab', { name: /Warnings/ })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('A warning')).toBeInTheDocument()
  })

  it('lets the BCBA switch lists', async () => {
    show({ missing: ['A required field'], warnings: ['A warning'] })
    expect(screen.getByText('A required field')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: /Draft flags/ }))
    expect(screen.getByText('Flag one')).toBeInTheDocument()
  })

  it('says so when nothing was flagged', () => {
    show({ missing: [], warnings: [], draft: { section_count: 9, sections_needing_review: 0, flags: [], used_custom_template: true }, discrepancies: [] })
    expect(screen.getByText('Nothing was flagged.')).toBeInTheDocument()
  })

  it('does not present a failed number check as zero discrepancies', () => {
    show({ discrepancies: null, check_error: 'cut off' })
    expect(screen.getByText("The automatic number check couldn't run")).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Numbers to verify' })).toHaveTextContent('n/a')
  })

  it('reports a draft that failed while keeping the imported data visible', () => {
    show({ draft: null, draft_error: 'model overloaded', discrepancies: null })
    expect(screen.getByText("The narrative couldn't be drafted")).toBeInTheDocument()
    expect(screen.getByText(/model overloaded/)).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Draft flags' })).toHaveTextContent('n/a')
  })

  it('points to the template screen when the built-in layout was used', () => {
    show()
    expect(screen.getByText(/Drafted in the built-in layout/)).toBeInTheDocument()
  })
})

describe('attentionLists', () => {
  it('keeps a fixed order and tolerates a missing draft or failed check', () => {
    const lists = attentionLists(result({ draft: null, discrepancies: null }))
    expect(lists.map((l) => l.key)).toEqual(['missing', 'warnings', 'flags', 'numbers'])
    expect(lists.find((l) => l.key === 'flags')?.items).toEqual([])
    expect(lists.find((l) => l.key === 'numbers')?.items).toEqual([])
  })
})
