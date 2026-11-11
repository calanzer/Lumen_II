import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { DeadlineBadge } from '@/components/clients/DeadlineBadge'
import { period } from '@/test/fixtures'

const tone = (overrides: Parameters<typeof period>[0]) => {
  render(<DeadlineBadge period={period(overrides)} />)
  return screen.getByText(/.+/)
}

describe('DeadlineBadge', () => {
  it('shows how long is left, with the urgency as a data attribute', () => {
    expect(tone({ days_until_end: 71 })).toHaveTextContent('71 days left')
  })

  it.each([
    [-5, 'expired', 'Ended 5 days ago'],
    [3, 'urgent', '3 days left'],
    [25, 'soon', '25 days left'],
    [90, 'ok', '90 days left'],
  ])('%i days -> %s', (days, expectedTone, text) => {
    const badge = tone({ days_until_end: days })
    expect(badge).toHaveAttribute('data-tone', expectedTone)
    expect(badge).toHaveTextContent(text)
  })

  it('shows the status instead of a countdown once the work is done', () => {
    const badge = tone({ status: 'exported', days_until_end: -30 })
    expect(badge).toHaveAttribute('data-tone', 'done')
    expect(badge).toHaveTextContent('Exported')
    expect(screen.queryByText(/Ended/)).not.toBeInTheDocument()
  })
})
