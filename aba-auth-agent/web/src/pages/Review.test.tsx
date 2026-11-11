import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api } from '@/lib/api'
import { Review } from '@/pages/Review'
import { clinicalData, periodDetail, validation } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { period: vi.fn(), saveData: vi.fn() } }
})
const mocked = vi.mocked(api)

function setup() {
  render(
    <MemoryRouter initialEntries={['/periods/p1/review']}>
      <Routes>
        <Route path="/periods/:periodId/review" element={<Review />} />
        <Route path="/periods/:periodId/generate" element={<p>generate screen</p>} />
        <Route path="/import" element={<p>import screen</p>} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

const lastSaved = () => mocked.saveData.mock.calls.at(-1)![1]

beforeEach(() => {
  vi.clearAllMocks()
  mocked.period.mockResolvedValue(periodDetail())
  mocked.saveData.mockImplementation(async (_id, data) => ({ data, validation: validation(), narrative_stale: false }))
})

describe('Review page', () => {
  it('shows who this is, the three steps and every section of the data', async () => {
    setup()
    expect(await screen.findByRole('heading', { name: 'Sam W.' })).toBeInTheDocument()
    expect(within(screen.getByRole('navigation', { name: 'Reauthorization steps' })).getByRole('link', { name: /Generate/ })).toHaveAttribute(
      'href',
      '/periods/p1/generate',
    )
    for (const title of [
      'Client demographics',
      'Assessments',
      'Skill acquisition targets',
      'Behavior reduction targets',
      'Hours utilization',
      'Treatment goals',
      'Caregiver training',
      'Discharge plan',
      'Requested hours for next authorization',
    ]) {
      expect(screen.getByRole('region', { name: new RegExp(title) })).toBeInTheDocument()
    }
    expect(screen.getByLabelText('Client ID')).toHaveValue('HB-1')
    expect(screen.getByLabelText('Age (years)')).toHaveValue('4')
    expect(screen.getByLabelText('Diagnosis codes')).toHaveValue('F84.0')
    expect(screen.getByText('1/2 mastered')).toBeInTheDocument()
  })

  it('asks for an import when the period has no data yet', async () => {
    mocked.period.mockResolvedValue(periodDetail({ data: null, validation: null, narrative: null }))
    setup()
    expect(await screen.findByText(/No report has been imported/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Import a report' })).toBeInTheDocument()
  })

  it('says so, with a retry, when the period cannot be loaded', async () => {
    mocked.period.mockRejectedValueOnce(new ApiError(404, 'Authorization period not found.'))
    const user = setup()
    expect(await screen.findByText('Authorization period not found.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { name: 'Sam W.' })).toBeInTheDocument()
  })

  it('shows what is missing and any warnings from the completeness check', async () => {
    mocked.period.mockResolvedValue(
      periodDetail({
        validation: validation({ is_complete: false, score: 0.7, missing: [{ description: 'Supervising BCBA name' }], warnings: ['CPT 97153: utilization is 58%'] }),
      }),
    )
    setup()
    expect(await screen.findByText('Data completeness: 70%')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Missing fields' })).toHaveTextContent('Supervising BCBA name')
    expect(screen.getByText('1 warning')).toBeInTheDocument()
  })

  it('saves an edit automatically, and a cleared number is saved as unknown, not 0', async () => {
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    await user.clear(screen.getByLabelText('Age (years)'))
    await user.type(screen.getByLabelText('Supervising BCBA'), ' Jr')

    await waitFor(() => expect(mocked.saveData).toHaveBeenCalled(), { timeout: 3000 })
    expect(lastSaved().client.age_years).toBeNull()
    expect(lastSaved().client.supervising_bcba).toBe('Dr. Gonzalez Jr')
    expect(await screen.findByText('All changes saved')).toBeInTheDocument()
  })

  it('"Save now" saves immediately', async () => {
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    await user.type(screen.getByLabelText('Supervising BCBA'), '!')
    await user.click(screen.getByRole('button', { name: 'Save now' }))
    expect(mocked.saveData).toHaveBeenCalledTimes(1)
  })

  it('shows why when a save is refused and keeps what was typed', async () => {
    mocked.saveData.mockRejectedValue(new ApiError(422, 'age_years: Input should be a valid integer'))
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    await user.type(screen.getByLabelText('Supervising BCBA'), '!')
    await user.click(screen.getByRole('button', { name: 'Save now' }))
    expect(await screen.findByText('Not saved: age_years: Input should be a valid integer')).toBeInTheDocument()
    expect(screen.getByLabelText('Supervising BCBA')).toHaveValue('Dr. Gonzalez!')
  })

  it('updates the completeness banner from the server after a save', async () => {
    mocked.saveData.mockImplementation(async (_id, data) => ({
      data,
      validation: validation({ is_complete: false, score: 0.5, missing: [{ description: 'Age' }] }),
      narrative_stale: false,
    }))
    const user = setup()
    await screen.findByText('Data completeness: 100%')
    await user.type(screen.getByLabelText('Supervising BCBA'), '!')
    await user.click(screen.getByRole('button', { name: 'Save now' }))
    expect(await screen.findByText('Data completeness: 50%')).toBeInTheDocument()
  })

  it('warns that the narrative is out of date once the data changes', async () => {
    mocked.saveData.mockImplementation(async (_id, data) => ({ data, validation: validation(), narrative_stale: true }))
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    expect(screen.queryByText(/changed the data since the narrative/)).not.toBeInTheDocument()
    await user.type(screen.getByLabelText('Supervising BCBA'), '!')
    await user.click(screen.getByRole('button', { name: 'Save now' }))
    expect(await screen.findByText(/changed the data since the narrative/)).toBeInTheDocument()
  })

  it('adds and removes list items, opening the new one', async () => {
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    const skills = screen.getByRole('region', { name: /Skill acquisition targets/ }) // the card
    await user.click(within(skills).getByRole('button', { name: /Add skill target/ }))
    expect(within(skills).getAllByRole('button', { name: /Remove this skill target/ })).toHaveLength(1) // only the open new one
    await user.type(within(skills).getByLabelText('Domain'), 'Play')
    await user.click(screen.getByRole('button', { name: 'Save now' }))
    expect(lastSaved().skill_acquisition_targets).toHaveLength(3)
    expect(lastSaved().skill_acquisition_targets[2].domain).toBe('Play')

    await user.click(within(skills).getByRole('button', { name: /Remove this skill target/ }))
    await user.click(screen.getByRole('button', { name: 'Save now' }))
    expect(lastSaved().skill_acquisition_targets).toHaveLength(2)
  })

  it('keeps the other items open when one is removed', async () => {
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    const skills = screen.getByRole('region', { name: /Skill acquisition targets/ })
    await user.click(within(skills).getByRole('button', { name: /Manding/ }))
    await user.click(within(skills).getByRole('button', { name: /Tacting/ }))
    expect(within(skills).getAllByRole('button', { name: /Remove this skill target/ })).toHaveLength(2)

    await user.click(within(skills).getAllByRole('button', { name: /Remove this skill target/ })[0])

    expect(within(skills).getByRole('button', { name: /Tacting/ })).toBeInTheDocument()
    expect(within(skills).queryByRole('button', { name: /Manding/ })).not.toBeInTheDocument()
    expect(within(skills).getAllByRole('button', { name: /Remove this skill target/ })).toHaveLength(1) // Tacting stayed open
  })

  it('only asks for the mastery date when a skill is marked mastered', async () => {
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    await user.click(screen.getByRole('button', { name: /Manding: Mands for 20 items/ }))
    expect(screen.queryByLabelText('Date mastered')).not.toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'Mastered' }))
    expect(screen.getByLabelText('Date mastered')).toBeInTheDocument()
  })

  it('requires a rationale for modified goals and warns about low utilization', async () => {
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    await user.click(screen.getByRole('button', { name: /Goal 1: Communication — modified/ }))
    expect(screen.getByText('A rationale is required for modified or discontinued goals.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /97153 — 58\/100 units \(58%\)/ }))
    expect(screen.getByText(/may require an explanation for utilization below 80%/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Explanation for low utilization/)).toBeInTheDocument()
  })

  it('recomputes utilization when the units change', async () => {
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    await user.click(screen.getByRole('button', { name: /97153 — 58\/100 units/ }))
    const used = screen.getByLabelText('Utilized units')
    await user.clear(used)
    await user.type(used, '90')
    expect(screen.getByText('90%')).toBeInTheDocument()
    expect(screen.queryByText(/may require an explanation/)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save now' }))
    expect(lastSaved().hours_utilization[0]).toMatchObject({ utilized_units: 90, utilization_pct: 90 })
  })

  it('shows the reduction from baseline for behaviors', async () => {
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    await user.click(screen.getByRole('button', { name: /\[decreasing\] Elopement/ }))
    expect(screen.getByText('Reduction from baseline: 60%')).toBeInTheDocument()
  })

  it('applies edits made in the raw JSON editor, and says when the JSON is broken', async () => {
    const user = setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    await user.click(screen.getByRole('button', { name: 'Raw JSON editor' }))
    const box = screen.getByLabelText('Extracted data JSON')
    expect((box as HTMLTextAreaElement).value).toContain('"supervising_bcba": "Dr. Gonzalez"')

    await user.clear(box)
    await user.click(box)
    await user.paste('{ nope')
    await user.click(screen.getByRole('button', { name: 'Apply JSON' }))
    expect(screen.getByText(/isn't valid JSON/)).toBeInTheDocument()

    await user.clear(box)
    await user.click(box)
    await user.paste(JSON.stringify(clinicalData({ clinical_justification_for_hours: 'Pasted in' })))
    await user.click(screen.getByRole('button', { name: 'Apply JSON' }))
    expect(await screen.findByLabelText('Clinical justification for requested hours')).toHaveValue('Pasted in')
    await waitFor(() => expect(lastSaved().clinical_justification_for_hours).toBe('Pasted in'), { timeout: 3000 })
  })

  it('lists extraction confidence notes and missing fields', async () => {
    mocked.period.mockResolvedValue(
      periodDetail({ data: clinicalData({ confidence_notes: ['Age was inferred'], missing_fields: ['caregiver barriers'] }) }),
    )
    setup()
    expect(await screen.findByText('Extraction confidence notes (1)')).toBeInTheDocument()
    expect(screen.getByText('Missing fields (1)')).toBeInTheDocument()
  })

  it('leads on to Generate', async () => {
    setup()
    await screen.findByRole('heading', { name: 'Sam W.' })
    expect(screen.getByRole('link', { name: /Continue to Generate/ })).toHaveAttribute('href', '/periods/p1/generate')
  })
})

