import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { AnswersForm } from '@/components/import/AnswersForm'
import type { Question } from '@/lib/types'
import { clients, payors } from '@/test/fixtures'

function setup(questions: Question[], error: string | null = null) {
  const onSubmit = vi.fn()
  render(<AnswersForm questions={questions} clients={clients} payors={payors} busy={false} error={error} onSubmit={onSubmit} />)
  return { onSubmit, user: userEvent.setup() }
}

describe('AnswersForm', () => {
  it('only asks about the dates when that is all the report left out', () => {
    setup(['period'])
    expect(screen.getByRole('button', { name: 'Authorization period start' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Authorization period end' })).toBeInTheDocument()
    expect(screen.queryByLabelText('New client ID')).not.toBeInTheDocument()
    expect(screen.queryByText('Payor')).not.toBeInTheDocument()
  })

  it('sends the default period as ISO dates, 182 days long', async () => {
    const { onSubmit, user } = setup(['period'])
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    const answers = onSubmit.mock.calls[0][0]
    expect(answers.period_start).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    const days = (new Date(answers.period_end).getTime() - new Date(answers.period_start).getTime()) / 86_400_000
    expect(Math.round(days)).toBe(182)
    expect(answers).not.toHaveProperty('new_identifier')
  })

  it('asks for a new client ID, and a payor because a new client needs one', async () => {
    const { onSubmit, user } = setup(['client', 'payor'])
    expect(screen.getByLabelText('New client ID')).toBeInTheDocument()
    expect(screen.getByText('Payor')).toBeInTheDocument()

    await user.type(screen.getByLabelText('New client ID'), '  HB-77 ')
    await user.click(screen.getByRole('combobox', { name: 'Payor' }))
    await user.click(await screen.findByRole('option', { name: 'Aetna' }))
    await user.click(screen.getByRole('button', { name: 'Continue' }))

    expect(onSubmit).toHaveBeenCalledWith({ new_identifier: 'HB-77', payor_key: 'aetna' })
  })

  it('drops the payor question when an existing client is chosen, and sends that client', async () => {
    const { onSubmit, user } = setup(['client', 'payor'])
    await user.click(screen.getByRole('combobox', { name: 'Which client is this report for?' }))
    await user.click(await screen.findByRole('option', { name: /Sam W\./ }))

    expect(screen.queryByText('Payor')).not.toBeInTheDocument() // an existing client already has one
    expect(screen.queryByLabelText('New client ID')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Continue' }))
    expect(onSubmit).toHaveBeenCalledWith({ existing_client_id: 'c1' })
  })

  it('shows the reason an answer was refused', () => {
    setup(['period'], 'The period must end after it starts.')
    expect(screen.getByText('The period must end after it starts.')).toBeInTheDocument()
  })

  it('clears an old refusal once the BCBA changes something, and shows it again if repeated', async () => {
    const onSubmit = vi.fn()
    const view = render(<AnswersForm questions={['client']} clients={clients} payors={payors} busy={false} error="Choose a client." onSubmit={onSubmit} />)
    expect(screen.getByText('Choose a client.')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('New client ID'), 'H')
    expect(screen.queryByText('Choose a client.')).not.toBeInTheDocument()

    // Submitting again and being refused again must show the message again
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
    view.rerender(<AnswersForm questions={['client']} clients={clients} payors={payors} busy={false} error="Choose a client." onSubmit={onSubmit} />)
    expect(screen.getByText('Choose a client.')).toBeInTheDocument()
  })
})
