import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DatePicker } from '@/components/DatePicker'

describe('DatePicker', () => {
  it('shows the chosen date, and a prompt when there is none', () => {
    const { rerender } = render(<DatePicker id="d" label="Start" value={new Date(2026, 9, 19)} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Start' })).toHaveTextContent('Oct 19, 2026')
    rerender(<DatePicker id="d" label="Start" value={undefined} onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Start' })).toHaveTextContent('Pick a date')
  })

  it('hands back the date that was clicked', async () => {
    const onChange = vi.fn()
    render(<DatePicker id="d" label="Start" value={new Date(2026, 9, 19)} onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: 'Start' }))
    await userEvent.click(await screen.findByRole('button', { name: /October 1st, 2026|October 1, 2026/ }))
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange.mock.calls[0][0]).toEqual(new Date(2026, 9, 1))
  })

  it('closes once a date is chosen, so it never covers the controls underneath', async () => {
    render(<DatePicker id="d" label="Start" value={new Date(2026, 9, 19)} onChange={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Start' }))
    await userEvent.click(await screen.findByRole('button', { name: /October 1st, 2026|October 1, 2026/ }))
    expect(screen.queryByRole('grid')).not.toBeInTheDocument()
  })

  it('cannot be cleared by clicking the selected day again', async () => {
    const onChange = vi.fn()
    render(<DatePicker id="d" label="Start" value={new Date(2026, 9, 19)} onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: 'Start' }))
    await userEvent.click(await screen.findByRole('button', { name: /October 19(th)?, 2026/ }))
    // The calendar passes extra arguments, so look at the date itself on every call
    const dates = onChange.mock.calls.map(([date]) => date)
    expect(dates.every((date) => date instanceof Date)).toBe(true)
  })
})
