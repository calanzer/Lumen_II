import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ClientDetailDialog } from '@/components/clients/ClientDetailDialog'
import { defaultDates } from '@/components/clients/NewPeriodForm'
import { ApiError, api } from '@/lib/api'
import { client, clientDetail, periodCard } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { clientDetail: vi.fn(), createPeriod: vi.fn(), saveNotes: vi.fn() } }
})
const mocked = vi.mocked(api)
beforeEach(() => vi.clearAllMocks())

function setup(target = client({ diagnosis_codes: ['F84.0', 'F80.2'] })) {
  const props = { onClose: vi.fn(), onImport: vi.fn(), onArchive: vi.fn(), onChanged: vi.fn() }
  render(
    <MemoryRouter>
      <ClientDetailDialog client={target} {...props} />
    </MemoryRouter>,
  )
  return { ...props, user: userEvent.setup(), target }
}

const full = periodCard({
  id: 'p2',
  period_start: '2026-07-01',
  period_end: '2026-12-31',
  status: 'generated',
  days_until_end: 120,
  has_data: true,
  has_narrative: true,
  notes: 'Mom prefers evenings',
  exported_at: null,
  validation: { score: 0.9, missing: 2, warnings: 3 },
  counts: { assessments: 3, skill_targets: 10, behaviors: 3, goals: 4, hours_codes: 5 },
  narrative: { confidence: 0.85, flags: 4 },
})
const empty = periodCard({ id: 'p1', period_start: '2026-01-01', period_end: '2026-06-30', status: 'draft', has_data: false, has_narrative: false, uploaded_filename: null, extracted_at: null })

describe('ClientDetailDialog', () => {
  it('shows who the client is straight away, before the periods load', () => {
    mocked.clientDetail.mockReturnValue(new Promise(() => {})) // never resolves
    setup()
    expect(screen.getByRole('heading', { name: 'Sam W.' })).toBeInTheDocument()
    expect(screen.getByText(/HB-1 · Aetna/)).toBeInTheDocument()
    expect(screen.getByLabelText('Diagnosis codes')).toHaveTextContent('F84.0')
    expect(screen.getByLabelText('Diagnosis codes')).toHaveTextContent('F80.2')
  })

  it('shows the newest period open, with its status, extraction summary and narrative confidence', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [full, empty] }))
    setup()
    expect(await screen.findByText(/Jul 1, 2026 to Dec 31, 2026/)).toBeInTheDocument()
    expect(screen.getByText('Narrative ready')).toBeInTheDocument()
    expect(screen.getByText('120 days left')).toBeInTheDocument()
    expect(screen.getByText(/Completeness:/).parentElement).toHaveTextContent('90% · Missing: 2 · Warnings: 3')
    const counts = screen.getByRole('list', { name: 'What was extracted' })
    expect(counts).toHaveTextContent('Skill targets: 10')
    expect(counts).toHaveTextContent('Hours codes: 5')
    expect(screen.getByText(/Narrative confidence:/).parentElement).toHaveTextContent('85% · BCBA flags: 4')
    expect(mocked.clientDetail).toHaveBeenCalledWith('c1')
  })

  it('offers Review, Generate and Export for a period that has a draft', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [full] }))
    setup()
    expect(await screen.findByRole('link', { name: 'Review data' })).toHaveAttribute('href', '/periods/p2/review')
    expect(screen.getByRole('link', { name: 'Generate' })).toHaveAttribute('href', '/periods/p2/generate')
    expect(screen.getByRole('link', { name: 'Export' })).toHaveAttribute('href', '/periods/p2/export')
    expect(screen.queryByRole('link', { name: 'Import a report' })).not.toBeInTheDocument()
  })

  it('offers only to import for a period with nothing in it, and no Export before there is a narrative', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [empty] }))
    setup()
    expect(await screen.findByRole('link', { name: 'Import a report' })).toHaveAttribute('href', '/import')
    expect(screen.queryByRole('link', { name: 'Review data' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Export' })).not.toBeInTheDocument()
    expect(screen.getByText('Not imported')).toBeInTheDocument()
  })

  it('offers Review and Generate but not Export for a period with data and no narrative yet', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [periodCard({ id: 'p5', has_data: true, has_narrative: false })] }))
    setup()
    expect(await screen.findByRole('link', { name: 'Review data' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Generate' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Export' })).not.toBeInTheDocument()
  })

  it('saves notes only when they have changed', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [full] }))
    mocked.saveNotes.mockResolvedValue({ notes: 'x' })
    const { user } = setup()
    const box = await screen.findByLabelText('BCBA notes')
    expect(box).toHaveValue('Mom prefers evenings')
    expect(screen.queryByRole('button', { name: 'Save notes' })).not.toBeInTheDocument()

    await user.type(box, ' and Tuesdays')
    await user.click(screen.getByRole('button', { name: 'Save notes' }))

    expect(mocked.saveNotes).toHaveBeenCalledWith('p2', 'Mom prefers evenings and Tuesdays')
    expect(await screen.findByText('Notes saved.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save notes' })).not.toBeInTheDocument()
  })

  it('shows why notes could not be saved and keeps them', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [full] }))
    mocked.saveNotes.mockRejectedValue(new ApiError(422, 'Keep notes under 5000 characters.'))
    const { user } = setup()
    await user.type(await screen.findByLabelText('BCBA notes'), '!')
    await user.click(screen.getByRole('button', { name: 'Save notes' }))
    expect(await screen.findByText('Keep notes under 5000 characters.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save notes' })).toBeInTheDocument() // still unsaved
  })

  it('creates a new period, dates prefilled, and shows it open at the top', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [empty] }))
    const created = periodCard({ id: 'p3', period_start: '2027-01-01', period_end: '2027-06-30', status: 'draft', has_data: false, has_narrative: false })
    mocked.createPeriod.mockResolvedValue(created)
    const { user, onChanged } = setup()
    await user.click(await screen.findByRole('button', { name: /New authorization period/ }))

    const { start, end } = defaultDates()
    expect(screen.getByLabelText('Period start')).toHaveValue(start)
    expect(screen.getByLabelText('Period end')).toHaveValue(end)
    await user.clear(screen.getByLabelText('Period start'))
    await user.type(screen.getByLabelText('Period start'), '2027-01-01')
    await user.clear(screen.getByLabelText('Period end'))
    await user.type(screen.getByLabelText('Period end'), '2027-06-30')
    await user.click(screen.getByRole('button', { name: 'Create period' }))

    expect(mocked.createPeriod).toHaveBeenCalledWith('c1', '2027-01-01', '2027-06-30')
    expect(await screen.findByRole('button', { name: /Jan 1, 2027 to Jun 30, 2027/ })).toHaveAttribute('aria-expanded', 'true')
    expect(onChanged).toHaveBeenCalled()
    expect(screen.queryByLabelText('Period start')).not.toBeInTheDocument() // form closed
  })

  it('opens a new period even when it is older than the others', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [full] }))
    mocked.createPeriod.mockResolvedValue(periodCard({ id: 'p0', period_start: '2025-01-01', period_end: '2025-06-30', status: 'draft', has_data: false, has_narrative: false }))
    const { user } = setup()
    await user.click(await screen.findByRole('button', { name: /New authorization period/ }))
    await user.click(screen.getByRole('button', { name: 'Create period' }))
    const older = await screen.findByRole('button', { name: /Jan 1, 2025 to Jun 30, 2025/ })
    expect(older).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /Jul 1, 2026 to Dec 31, 2026/ })).toHaveAttribute('aria-expanded', 'false')
  })

  it('will not create a period that ends before it starts, or refused by the server', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [empty] }))
    const { user } = setup()
    await user.click(await screen.findByRole('button', { name: /New authorization period/ }))
    await user.clear(screen.getByLabelText('Period end'))
    await user.type(screen.getByLabelText('Period end'), '2000-01-01')
    await user.click(screen.getByRole('button', { name: 'Create period' }))
    expect(screen.getByText('The period must end after it starts.')).toBeInTheDocument()
    expect(mocked.createPeriod).not.toHaveBeenCalled()

    mocked.createPeriod.mockRejectedValue(new ApiError(404, 'Client not found.'))
    await user.clear(screen.getByLabelText('Period end'))
    await user.type(screen.getByLabelText('Period end'), '2099-01-01')
    await user.click(screen.getByRole('button', { name: 'Create period' }))
    expect(await screen.findByText('Client not found.')).toBeInTheDocument()
  })

  it('shows VB-MAPP trends across periods when there are two or more', async () => {
    mocked.clientDetail.mockResolvedValue(
      clientDetail({
        periods: [full],
        trends: { columns: ['2025-01', '2025-07'], rows: [{ domain: 'Mand', values: [3, 6] }, { domain: 'Tact', values: [null, 5] }] },
      }),
    )
    setup()
    const table = within(await screen.findByRole('table'))
    expect(table.getByRole('columnheader', { name: '2025-07' })).toBeInTheDocument()
    expect(table.getByRole('row', { name: /Mand 3 6/ })).toBeInTheDocument()
    expect(table.getByRole('row', { name: /Tact — 5/ })).toBeInTheDocument()
  })

  it('has no trends table without enough data', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ periods: [full] }))
    setup()
    await screen.findByText(/Jul 1, 2026/)
    expect(screen.queryByText('VB-MAPP domain scores over time')).not.toBeInTheDocument()
  })

  it('says so when nothing has been imported for the client', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ ...client({ latest_period: null, period_count: 0 }) }))
    setup()
    expect(await screen.findByText('No reports imported yet for this client.')).toBeInTheDocument()
  })

  it('shows a load failure instead of an empty list', async () => {
    mocked.clientDetail.mockRejectedValue(new ApiError(404, 'Client not found.'))
    setup()
    expect(await screen.findByText('Client not found.')).toBeInTheDocument()
    expect(screen.queryByText(/No reports imported yet/)).not.toBeInTheDocument()
  })

  it('hands the client to import and archive', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail())
    const { user, onImport, onArchive, target } = setup()
    await user.click(screen.getByRole('button', { name: 'Import a report' }))
    expect(onImport).toHaveBeenCalledWith(target)
    await user.click(screen.getByRole('button', { name: 'Archive client' }))
    expect(onArchive).toHaveBeenCalledWith(target)
  })
})

