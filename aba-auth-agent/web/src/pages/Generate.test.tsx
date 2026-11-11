import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api } from '@/lib/api'
import { Generate } from '@/pages/Generate'
import { generation, narrative, periodDetail, validation } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { period: vi.fn(), generation: vi.fn(), startGeneration: vi.fn(), saveNarrative: vi.fn() } }
})
const mocked = vi.mocked(api)

function setup() {
  render(
    <MemoryRouter initialEntries={['/periods/p1/generate']}>
      <Routes>
        <Route path="/periods/:periodId/generate" element={<Generate />} />
        <Route path="/periods/:periodId/export" element={<p>export screen</p>} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
}

const comparison = {
  prior_start: '2025-07-01',
  prior_end: '2025-12-31',
  skills_mastered_prior: 2,
  skills_mastered: 5,
  skill_targets: 10,
  behavior_targets: 3,
  behavior_changes: [
    { name: 'Aggression', prior: 5.4, current: 2.7, unit: 'per hour', percent_change: -50 },
    { name: 'Elopement', prior: 1, current: 1.5, unit: 'per hour', percent_change: 50 },
  ],
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  vi.clearAllMocks()
  mocked.period.mockResolvedValue(periodDetail())
  mocked.generation.mockResolvedValue(generation())
  mocked.saveNarrative.mockImplementation(async () => narrative())
})
afterEach(() => vi.useRealTimers())

const flush = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms))

describe('Generate page', () => {
  it('shows each section with its source data and editable text, and which ones need review', async () => {
    setup()
    expect(await screen.findByRole('button', { name: /1\. Client Overview/ })).toBeInTheDocument()
    // the section that needs review starts open, with its note
    expect(screen.getByText('Review needed: Utilization is low.')).toBeInTheDocument()
    expect((screen.getByLabelText('Edit Hours Utilization & Justification') as HTMLTextAreaElement).value).toContain('Hours were used.')
    expect(screen.getByLabelText('Source data for Hours Utilization & Justification')).toHaveTextContent('"cpt_code": "97153"')
    // the other doesn't, until opened
    expect(screen.queryByLabelText('Edit Client Overview')).not.toBeInTheDocument()
    expect(screen.getByText('Needs review')).toBeInTheDocument()
    expect(screen.getByText('OK')).toBeInTheDocument()
  })

  it('hints when a section is too short or too long for a payor', async () => {
    const user = setup()
    await screen.findByRole('button', { name: /1\. Client Overview/ })
    await user.click(screen.getByRole('button', { name: /1\. Client Overview/ }))
    expect(screen.getByText('5 words — may be too brief for the payor')).toBeInTheDocument()
    expect(screen.getByText('180 words')).toBeInTheDocument() // the open hours section: in range, no warning
  })

  it('flags a section that has run long', async () => {
    mocked.period.mockResolvedValue(
      periodDetail({ narrative: narrative({ sections: [{ ...narrative().sections[0], content: 'word '.repeat(450) }, narrative().sections[1]] }) }),
    )
    const user = setup()
    await user.click(await screen.findByRole('button', { name: /1\. Client Overview/ }))
    expect(screen.getByText('450 words — consider condensing')).toBeInTheDocument()
  })

  it('says when the AI listed no source fields for a section', async () => {
    mocked.period.mockResolvedValue(periodDetail({ narrative: narrative({ sections: [{ ...narrative().sections[1], source: {} }] }) }))
    setup()
    expect(await screen.findByText('The AI did not list specific source fields for this section.')).toBeInTheDocument()
  })

  it('lists the items needing BCBA attention', async () => {
    setup()
    const flags = await screen.findByRole('region', { name: 'Items requiring BCBA attention' })
    expect(within(flags).getByText('Check the utilization explanation')).toBeInTheDocument()
  })

  it('shows progress since the prior authorization when there is one', async () => {
    mocked.period.mockResolvedValue(periodDetail({ comparison }))
    setup()
    expect(await screen.findByText('Progress since prior authorization')).toBeInTheDocument()
    expect(screen.getByText('+3')).toBeInTheDocument() // skills mastered 2 → 5
    expect(screen.getByText(/5.4 → 2.7 per hour/)).toBeInTheDocument()
    expect(screen.getByText('50% decrease')).toBeInTheDocument()
    expect(screen.getByText('50% increase')).toBeInTheDocument()
  })

  it('has no comparison card without a prior period', async () => {
    setup()
    await screen.findByRole('button', { name: /1\. Client Overview/ })
    expect(screen.queryByText('Progress since prior authorization')).not.toBeInTheDocument()
  })

  it('warns about incomplete data, and about a stale draft', async () => {
    mocked.period.mockResolvedValue(
      periodDetail({ validation: validation({ is_complete: false, score: 0.7 }), narrative: narrative({ stale: true }) }),
    )
    setup()
    expect(await screen.findByText('Extracted data is incomplete (70%)')).toBeInTheDocument()
    expect(screen.getByText(/written before your latest edits/)).toBeInTheDocument()
  })

  it('says which layout it will use', async () => {
    mocked.period.mockResolvedValue(periodDetail({ template: { name: 'Our Aetna report', section_count: 7 } }))
    setup()
    expect(await screen.findByText(/your template “Our Aetna report” \(7 sections\)/)).toBeInTheDocument()
  })

  it('first-time generation: starts, shows progress, then loads the draft and the cross-check', async () => {
    mocked.period.mockResolvedValueOnce(periodDetail({ narrative: null, status: 'in_progress' }))
    mocked.startGeneration.mockResolvedValue(generation({ stage: 'drafting' }))
    mocked.generation
      .mockResolvedValueOnce(generation())
      .mockResolvedValueOnce(generation({ stage: 'checking' }))
      .mockResolvedValue(generation({ stage: 'done', discrepancies: ['[S] Claim: x (value: 9) could not be traced'] }))
    const user = setup()

    await user.click(await screen.findByRole('button', { name: 'Generate Aetna narrative' })) // no confirm: nothing to replace
    expect(mocked.startGeneration).toHaveBeenCalledWith('p1')
    expect(screen.getByRole('list', { name: 'Progress' })).toHaveTextContent('Writing the narrative')
    expect(screen.getByRole('button', { name: /Generate Aetna narrative/ })).toBeDisabled()

    await flush(1600)
    expect(screen.getByRole('list', { name: 'Progress' })).toHaveTextContent('Cross-checking the numbers')
    await flush(1600)

    expect(await screen.findByText('1 potential discrepancy found')).toBeInTheDocument()
    expect(screen.getByText(/could not be traced/)).toBeInTheDocument()
    expect(mocked.period).toHaveBeenCalledTimes(2) // reloaded to get the new draft
    expect(await screen.findByRole('button', { name: /1\. Client Overview/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Regenerate Aetna narrative' })).toBeEnabled()
  })

  it('says when the cross-check found nothing, and when it could not run', async () => {
    mocked.startGeneration.mockResolvedValue(generation({ stage: 'drafting' }))
    mocked.generation.mockResolvedValueOnce(generation()).mockResolvedValue(generation({ stage: 'done', discrepancies: [] }))
    const user = setup()
    await user.click(await screen.findByRole('button', { name: 'Regenerate Aetna narrative' }))
    await user.click(screen.getByRole('button', { name: 'Regenerate' }))
    await flush(1600)
    expect(await screen.findByText('No discrepancies detected in the cross-check.')).toBeInTheDocument()
  })

  it('does not hide a cross-check that could not run behind "no discrepancies"', async () => {
    mocked.startGeneration.mockResolvedValue(generation({ stage: 'drafting' }))
    mocked.generation
      .mockResolvedValueOnce(generation())
      .mockResolvedValue(generation({ stage: 'done', discrepancies: null, check_error: 'model overloaded' }))
    const user = setup()
    await user.click(await screen.findByRole('button', { name: 'Regenerate Aetna narrative' }))
    await user.click(screen.getByRole('button', { name: 'Regenerate' }))
    await flush(1600)
    expect(await screen.findByText("The automatic number check couldn't run")).toBeInTheDocument()
    expect(screen.getByText('model overloaded')).toBeInTheDocument()
    expect(screen.queryByText(/No discrepancies detected/)).not.toBeInTheDocument()
  })

  it('reports a failed generation and says the previous draft is untouched', async () => {
    mocked.startGeneration.mockResolvedValue(generation({ stage: 'drafting' }))
    mocked.generation.mockResolvedValueOnce(generation()).mockResolvedValue(generation({ stage: 'error', error: 'model overloaded' }))
    const user = setup()
    await user.click(await screen.findByRole('button', { name: 'Regenerate Aetna narrative' }))
    await user.click(screen.getByRole('button', { name: 'Regenerate' }))
    await flush(1600)
    expect(await screen.findByText('Generation failed')).toBeInTheDocument()
    expect(screen.getByText(/model overloaded Your previous draft is unchanged\./)).toBeInTheDocument()
  })

  it('asks before replacing an existing draft, and leaves it alone if you decline', async () => {
    const user = setup()
    await user.click(await screen.findByRole('button', { name: 'Regenerate Aetna narrative' }))
    expect(screen.getByText('Replace the current draft?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Keep my draft' }))
    expect(mocked.startGeneration).not.toHaveBeenCalled()
  })

  it('saves edits to the narrative text automatically, all sections together', async () => {
    const user = setup()
    const box = await screen.findByLabelText('Edit Hours Utilization & Justification')
    await user.clear(box)
    await user.type(box, 'Rewritten by me.')
    await flush(1000)
    await waitFor(() => expect(mocked.saveNarrative).toHaveBeenCalled())
    const [, sections] = mocked.saveNarrative.mock.calls.at(-1)!
    expect(sections).toEqual([
      { key: 'client_overview', content: 'Short overview of the client.' },
      { key: 'hours_justification', content: 'Rewritten by me.' },
    ])
    expect(await screen.findByText('All changes saved')).toBeInTheDocument()
  })

  it('shows why a save was refused and keeps the text', async () => {
    mocked.saveNarrative.mockRejectedValue(new ApiError(422, 'This narrative has no section “x”.'))
    const user = setup()
    const box = await screen.findByLabelText('Edit Hours Utilization & Justification')
    await user.type(box, '!')
    await user.click(screen.getByRole('button', { name: 'Save all edits' }))
    expect(await screen.findByText(/Not saved: This narrative has no section/)).toBeInTheDocument()
    expect((box as HTMLTextAreaElement).value).toMatch(/!$/)
  })

  it('does not let a pending edit overwrite a draft you chose to regenerate', async () => {
    mocked.startGeneration.mockResolvedValue(generation({ stage: 'drafting' }))
    mocked.generation.mockResolvedValueOnce(generation()).mockResolvedValue(generation({ stage: 'done', discrepancies: [] }))
    const user = setup()
    const box = await screen.findByLabelText('Edit Hours Utilization & Justification')
    await user.type(box, ' LATE EDIT')
    await user.click(screen.getByRole('button', { name: 'Regenerate Aetna narrative' }))
    await user.click(screen.getByRole('button', { name: 'Regenerate' }))
    await flush(5000) // long past the autosave delay, and the new draft has arrived
    expect(mocked.saveNarrative).not.toHaveBeenCalled()
  })

  it('leads on to Export', async () => {
    setup()
    expect(await screen.findByRole('link', { name: /Continue to Export/ })).toHaveAttribute('href', '/periods/p1/export')
  })

  it('asks for an import when there is no data yet', async () => {
    mocked.period.mockResolvedValue(periodDetail({ data: null, narrative: null, validation: null }))
    setup()
    expect(await screen.findByText(/No report has been imported/)).toBeInTheDocument()
  })

  it('the step bar only offers Export once there is a narrative', async () => {
    mocked.period.mockResolvedValue(periodDetail({ narrative: null }))
    setup()
    const steps = within(await screen.findByRole('navigation', { name: 'Reauthorization steps' }))
    expect(steps.getByRole('link', { name: /Review data/ })).toBeInTheDocument()
    expect(steps.queryByRole('link', { name: /Export/ })).not.toBeInTheDocument()
  })
})
