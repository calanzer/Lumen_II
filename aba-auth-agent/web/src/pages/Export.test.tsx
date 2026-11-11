import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api } from '@/lib/api'
import { saveBlob } from '@/lib/files'
import { Export } from '@/pages/Export'
import { narrative, payors, periodDetail } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { period: vi.fn(), payors: vi.fn(), exportPeriod: vi.fn(), markSubmitted: vi.fn() } }
})
vi.mock('@/lib/files', () => ({ saveBlob: vi.fn() }))
const mocked = vi.mocked(api)

const file = { blob: new Blob(['docx']), filename: 'reauth_aetna_HB-1_2026-06-30.docx' }

function setup() {
  render(
    <MemoryRouter initialEntries={['/periods/p1/export']}>
      <Routes>
        <Route path="/periods/:periodId/export" element={<Export />} />
        <Route path="/periods/:periodId/generate" element={<p>generate screen</p>} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

const confirm = (user: ReturnType<typeof userEvent.setup>) =>
  user.click(screen.getByRole('checkbox', { name: /I have reviewed all sections/ }))
const exportButton = () => screen.getByRole('button', { name: 'Generate Word document' })

beforeEach(() => {
  vi.clearAllMocks()
  mocked.period.mockResolvedValue(periodDetail())
  mocked.payors.mockResolvedValue(payors)
  mocked.exportPeriod.mockResolvedValue(file)
  mocked.markSubmitted.mockResolvedValue({ status: 'submitted' })
})

describe('Export page', () => {
  it('summarizes confidence, flags and the sections still needing review', async () => {
    setup()
    const summary = within(await screen.findByRole('region', { name: 'Export summary' }))
    expect(summary.getByText('85%')).toBeInTheDocument()
    expect(summary.getByText('BCBA flags').nextSibling).toHaveTextContent('1')
    expect(summary.getByText('Sections needing review').nextSibling).toHaveTextContent('1')
    expect(summary.getByText('1 section still needs review.')).toBeInTheDocument()
  })

  it('has no review warning when every section is fine', async () => {
    const clean = narrative()
    clean.sections.forEach((s) => (s.requires_review = false))
    mocked.period.mockResolvedValue(periodDetail({ narrative: { ...clean, flags: [] } }))
    setup()
    await screen.findByRole('region', { name: 'Export summary' })
    expect(screen.queryByText(/still needs? review|still need review/)).not.toBeInTheDocument()
  })

  it('warns when the narrative is older than the data, pointing back to Generate', async () => {
    mocked.period.mockResolvedValue(periodDetail({ narrative: narrative({ stale: true }) }))
    setup()
    expect(await screen.findByText(/written before your latest edits/)).toBeInTheDocument()
    const warning = screen.getByText(/written before your latest edits/).closest('[role="alert"]') as HTMLElement
    expect(within(warning).getByRole('link', { name: 'Generate' })).toHaveAttribute('href', '/periods/p1/generate')
  })

  it('will not build the document until the accuracy confirmation is ticked', async () => {
    const user = setup()
    await screen.findByRole('region', { name: 'Export summary' })
    expect(exportButton()).toBeDisabled()
    await confirm(user)
    expect(exportButton()).toBeEnabled()
    await confirm(user)
    expect(exportButton()).toBeDisabled()
    expect(mocked.exportPeriod).not.toHaveBeenCalled()
  })

  it('builds and downloads the document, then shows it as ready and reloads the period', async () => {
    const user = setup()
    await screen.findByRole('region', { name: 'Export summary' })
    await confirm(user)
    await user.click(exportButton())

    expect(mocked.exportPeriod).toHaveBeenCalledWith('p1', 'aetna') // the client's payor is the default
    expect(saveBlob).toHaveBeenCalledWith(file.blob, file.filename)
    expect(await screen.findByText(`Document ready: ${file.filename}`)).toBeInTheDocument()
    expect(mocked.period).toHaveBeenCalledTimes(2)

    await user.click(screen.getByRole('button', { name: /Download again/ }))
    expect(saveBlob).toHaveBeenCalledTimes(2)
  })

  it('uses the payor chosen for a built-in narrative', async () => {
    const user = setup()
    await screen.findByRole('region', { name: 'Export summary' })
    await user.click(screen.getByRole('combobox', { name: /payor template/i }))
    await user.click(await screen.findByRole('option', { name: /Optum/ }))
    await confirm(user)
    await user.click(exportButton())
    expect(mocked.exportPeriod).toHaveBeenCalledWith('p1', 'optum')
  })

  it('a template-driven narrative has no payor picker and exports with its own layout', async () => {
    mocked.period.mockResolvedValue(
      periodDetail({ narrative: narrative({ kind: 'custom', payor_key: 'aetna', template_name: 'Our Aetna report' }) }),
    )
    const user = setup()
    expect(await screen.findByText(/follows your template “Our Aetna report” for Aetna/)).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    await confirm(user)
    await user.click(exportButton())
    expect(mocked.exportPeriod).toHaveBeenCalledWith('p1', undefined)
  })

  it('shows why an export failed and does not claim the document is ready', async () => {
    mocked.exportPeriod.mockRejectedValue(new ApiError(500, 'The Word document couldn\'t be built: template missing'))
    const user = setup()
    await screen.findByRole('region', { name: 'Export summary' })
    await confirm(user)
    await user.click(exportButton())
    expect(await screen.findByText(/template missing/)).toBeInTheDocument()
    expect(screen.queryByText(/Document ready/)).not.toBeInTheDocument()
    expect(saveBlob).not.toHaveBeenCalled()
  })

  it('offers "mark as submitted" only after the document has been exported', async () => {
    setup()
    await screen.findByRole('region', { name: 'Export summary' })
    expect(screen.queryByRole('button', { name: /Mark as submitted/ })).not.toBeInTheDocument()
  })

  it('marks an exported period as submitted', async () => {
    mocked.period
      .mockResolvedValueOnce(periodDetail({ status: 'exported', exported_at: '2026-02-01T10:00:00' }))
      .mockResolvedValue(periodDetail({ status: 'submitted', exported_at: '2026-02-01T10:00:00' }))
    const user = setup()
    await user.click(await screen.findByRole('button', { name: /Mark as submitted to payor/ }))
    expect(mocked.markSubmitted).toHaveBeenCalledWith('p1')
    expect(await screen.findByText('Submitted to the payor')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Mark as submitted/ })).not.toBeInTheDocument()
  })

  it('sends you to Generate when there is no narrative yet', async () => {
    mocked.period.mockResolvedValue(periodDetail({ narrative: null }))
    setup()
    expect(await screen.findByText('No narrative has been written yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to Generate' })).toHaveAttribute('href', '/periods/p1/generate')
  })
})
