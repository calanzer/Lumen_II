import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api } from '@/lib/api'
import { Templates } from '@/pages/Templates'
import { payors } from '@/test/fixtures'
import type { TemplateInfo } from '@/lib/types'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { payors: vi.fn(), template: vi.fn(), analyzeTemplate: vi.fn(), saveTemplate: vi.fn(), useDefaultTemplate: vi.fn() } }
})
const mocked = vi.mocked(api)

const DEFAULTS = ['Client Overview', 'Assessment Summary']
const builtIn = (payor = 'aetna', name = 'Aetna'): TemplateInfo => ({ payor, payor_name: name, active: null, default_sections: DEFAULTS })
const custom = (): TemplateInfo => ({
  ...builtIn(),
  active: {
    name: 'Our Aetna report',
    style_notes: 'Formal, third person.',
    source_filename: 'old.pdf',
    sections: [{ title: 'Summary', guidance: 'Overview of progress' }, { title: 'Plan', guidance: '' }],
  },
})
const analysis = {
  source_filename: 'old report.pdf',
  style_notes: 'Plain language.',
  sections: [{ title: 'Summary', guidance: 'Overview' }, { title: 'Goals', guidance: 'Goal progress' }, { title: 'Hours', guidance: '' }],
}

const pdf = () => new File(['x'], 'old report.pdf', { type: 'application/pdf' })

beforeEach(() => {
  vi.clearAllMocks()
  mocked.payors.mockResolvedValue(payors)
  mocked.template.mockImplementation(async (payor) => builtIn(payor, payor === 'aetna' ? 'Aetna' : 'Optum / UnitedHealthcare'))
  mocked.analyzeTemplate.mockResolvedValue(analysis)
  mocked.saveTemplate.mockResolvedValue(custom())
  mocked.useDefaultTemplate.mockResolvedValue(builtIn())
})

async function analyzeFile(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByText('Using the built-in default layout')
  await user.upload(screen.getByLabelText('Past report'), pdf())
  await user.click(screen.getByRole('button', { name: 'Analyze report' }))
  return await screen.findByRole('region', { name: 'Review the detected sections' }).catch(() => screen.findByLabelText('Review the detected sections'))
}

describe('Templates page', () => {
  it('starts on the first payor, showing the built-in layout', async () => {
    render(<Templates />)
    expect(await screen.findByText('Using the built-in default layout')).toBeInTheDocument()
    expect(screen.getByText(/Nine standard sections: Client Overview, Assessment Summary/)).toBeInTheDocument()
    expect(mocked.template).toHaveBeenCalledWith('aetna')
  })

  it('shows the active template, its sections and style', async () => {
    mocked.template.mockResolvedValue(custom())
    render(<Templates />)
    expect(await screen.findByText('Using your template: Our Aetna report')).toBeInTheDocument()
    expect(screen.getByText('Summary')).toBeInTheDocument()
    expect(screen.getByText(/Overview of progress/)).toBeInTheDocument()
    expect(screen.getByText('Style: Formal, third person.')).toBeInTheDocument()
  })

  it('switches back to the built-in default', async () => {
    mocked.template.mockResolvedValue(custom())
    const user = userEvent.setup()
    render(<Templates />)
    await user.click(await screen.findByRole('button', { name: 'Use the built-in default instead' }))
    expect(mocked.useDefaultTemplate).toHaveBeenCalledWith('aetna')
    expect(await screen.findByText('Using the built-in default layout')).toBeInTheDocument()
    expect(screen.getByText('Now using the built-in layout.')).toBeInTheDocument()
  })

  it('loads the other payor when you choose it', async () => {
    const user = userEvent.setup()
    render(<Templates />)
    await screen.findByText('Using the built-in default layout')
    await user.click(screen.getByRole('combobox', { name: 'Payor' }))
    await user.click(await screen.findByRole('option', { name: /Optum/ }))
    await waitFor(() => expect(mocked.template).toHaveBeenCalledWith('optum'))
  })

  it('cannot analyze until a report is chosen, and refuses other file types', async () => {
    const user = userEvent.setup({ applyAccept: false })
    render(<Templates />)
    await screen.findByText('Using the built-in default layout')
    expect(screen.getByRole('button', { name: 'Analyze report' })).toBeDisabled()
    await user.upload(screen.getByLabelText('Past report'), new File(['x'], 'notes.txt'))
    expect(screen.getByText('Upload a PDF or Word (.docx) report.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyze report' })).toBeDisabled()
  })

  it('analyzes a past report into editable sections with the style and a suggested name', async () => {
    const user = userEvent.setup()
    render(<Templates />)
    const review = within(await analyzeFile(user))
    expect(mocked.analyzeTemplate).toHaveBeenCalledWith(expect.objectContaining({ name: 'old report.pdf' }))
    expect(review.getByLabelText('Section 1 title')).toHaveValue('Summary')
    expect(review.getByLabelText('Section 2 covers')).toHaveValue('Goal progress')
    expect(review.getByLabelText('Writing style')).toHaveValue('Plain language.')
    expect(review.getByLabelText('Template name')).toHaveValue('Aetna — old report.pdf')
    expect(mocked.saveTemplate).not.toHaveBeenCalled() // nothing is saved until asked
  })

  it('saves the edited template: renamed, reordered, extended and trimmed', async () => {
    const user = userEvent.setup()
    render(<Templates />)
    const review = within(await analyzeFile(user))

    await user.clear(review.getByLabelText('Section 1 title'))
    await user.type(review.getByLabelText('Section 1 title'), 'Overview')
    await user.click(review.getByRole('button', { name: 'Move section 3 up' })) // Hours before Goals
    await user.click(review.getByRole('button', { name: 'Add section' }))
    await user.type(review.getByLabelText('Section 4 title'), 'Discharge')
    await user.clear(review.getByLabelText('Template name'))
    await user.type(review.getByLabelText('Template name'), 'Aetna house style')
    await user.click(review.getByRole('button', { name: 'Save template' }))

    expect(mocked.saveTemplate).toHaveBeenCalledWith('aetna', 'Aetna house style', {
      source_filename: 'old report.pdf',
      style_notes: 'Plain language.',
      sections: [
        { title: 'Overview', guidance: 'Overview' },
        { title: 'Hours', guidance: '' },
        { title: 'Goals', guidance: 'Goal progress' },
        { title: 'Discharge', guidance: '' },
      ],
    })
    expect(await screen.findByText('Template saved for Aetna.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Review the detected sections')).not.toBeInTheDocument()
    expect(screen.getByText('Using your template: Our Aetna report')).toBeInTheDocument()
  })

  it('deletes a section', async () => {
    const user = userEvent.setup()
    render(<Templates />)
    const review = within(await analyzeFile(user))
    await user.click(review.getByRole('button', { name: 'Delete section 2' }))
    expect(review.queryByDisplayValue('Goals')).not.toBeInTheDocument()
    expect(review.getByLabelText('Section 2 title')).toHaveValue('Hours')
  })

  it('will not save without two sections or without a name, saying what is wrong', async () => {
    const user = userEvent.setup()
    render(<Templates />)
    const review = within(await analyzeFile(user))
    await user.click(review.getByRole('button', { name: 'Delete section 3' }))
    await user.click(review.getByRole('button', { name: 'Delete section 2' }))
    await user.click(review.getByRole('button', { name: 'Save template' }))
    expect(screen.getByText('A template needs at least two sections.')).toBeInTheDocument()

    await user.click(review.getByRole('button', { name: 'Add section' }))
    await user.type(review.getByLabelText('Section 2 title'), 'Plan')
    await user.clear(review.getByLabelText('Template name'))
    await user.click(review.getByRole('button', { name: 'Save template' }))
    expect(screen.getByText('Give the template a name.')).toBeInTheDocument()
    expect(mocked.saveTemplate).not.toHaveBeenCalled()
  })

  it('discarding throws the draft away without saving', async () => {
    const user = userEvent.setup()
    render(<Templates />)
    const review = within(await analyzeFile(user))
    await user.click(review.getByRole('button', { name: 'Discard' }))
    expect(screen.queryByLabelText('Review the detected sections')).not.toBeInTheDocument()
    expect(mocked.saveTemplate).not.toHaveBeenCalled()
  })

  it('keeps the draft if saving fails, and says why', async () => {
    mocked.saveTemplate.mockRejectedValue(new ApiError(422, 'The name or writing style is too long.'))
    const user = userEvent.setup()
    render(<Templates />)
    const review = within(await analyzeFile(user))
    await user.click(review.getByRole('button', { name: 'Save template' }))
    expect(await screen.findByText('The name or writing style is too long.')).toBeInTheDocument()
    expect(review.getByLabelText('Section 1 title')).toHaveValue('Summary')
  })

  it('says why a report could not be analyzed', async () => {
    mocked.analyzeTemplate.mockRejectedValue(new ApiError(422, 'Could not analyze that report: no sections found'))
    const user = userEvent.setup()
    render(<Templates />)
    await screen.findByText('Using the built-in default layout')
    await user.upload(screen.getByLabelText('Past report'), pdf())
    await user.click(screen.getByRole('button', { name: 'Analyze report' }))
    expect(await screen.findByText(/no sections found/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Review the detected sections')).not.toBeInTheDocument()
  })

  it('keeps a separate draft for each payor', async () => {
    const user = userEvent.setup()
    render(<Templates />)
    await analyzeFile(user)
    await user.click(screen.getByRole('combobox', { name: 'Payor' }))
    await user.click(await screen.findByRole('option', { name: /Optum/ }))
    await screen.findByText('Using the built-in default layout')
    expect(screen.queryByLabelText('Review the detected sections')).not.toBeInTheDocument()
    await user.click(screen.getByRole('combobox', { name: 'Payor' }))
    await user.click(await screen.findByRole('option', { name: 'Aetna' }))
    expect(await screen.findByLabelText('Review the detected sections')).toBeInTheDocument()
  })
})
