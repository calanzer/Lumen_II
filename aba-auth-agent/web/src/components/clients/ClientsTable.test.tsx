import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ClientsTable, type ClientsTableProps } from '@/components/clients/ClientsTable'
import { client, period } from '@/test/fixtures'

function setup(overrides: Partial<ClientsTableProps> = {}) {
  const props: ClientsTableProps = {
    clients: [
      client({ id: 'a', display_name: 'Abe A.', client_identifier: 'CR-1', diagnosis_codes: ['F84.0', 'F80.2'], latest_period: period({ days_until_end: 9, period_end: '2026-06-30' }) }),
      client({ id: 'b', display_name: 'Bea B.', client_identifier: null, diagnosis_codes: [], latest_period: null, period_count: 0 }),
    ],
    sort: { key: 'deadline', dir: 'asc' },
    onSort: vi.fn(),
    onOpen: vi.fn(),
    onImport: vi.fn(),
    onArchive: vi.fn(),
    ...overrides,
  }
  render(<ClientsTable {...props} />)
  return { props, user: userEvent.setup() }
}

describe('ClientsTable', () => {
  it('shows each client with their ID, diagnosis, payor and authorization', () => {
    setup()
    const abe = screen.getByRole('row', { name: /Abe A\./ })
    expect(within(abe).getByText('CR-1')).toBeInTheDocument()
    expect(within(abe).getByText('F84.0, F80.2')).toBeInTheDocument()
    // The payor appears once per layout: under the name on phones, in its own column from sm up
    const payor = within(abe).getAllByText('Aetna')
    expect(payor).toHaveLength(2)
    expect(payor.some((el) => el.className.includes('sm:hidden'))).toBe(true)
    expect(payor.some((el) => el.closest('td')?.className.includes('hidden sm:table-cell'))).toBe(true)
    expect(within(abe).getByText(/Ends Jun 30, 2026/)).toBeInTheDocument()
    expect(within(abe).getByText('9 days left')).toBeInTheDocument()
  })

  it('says plainly when there is no client ID, diagnosis or report yet', () => {
    setup()
    const bea = screen.getByRole('row', { name: /Bea B\./ })
    expect(within(bea).getByText('No client ID')).toBeInTheDocument()
    expect(within(bea).getByText('—')).toBeInTheDocument()
    expect(within(bea).getByText('No reports yet')).toBeInTheDocument()
  })

  it('opens a client by double-click or by activating their name', async () => {
    const { props, user } = setup()
    await user.dblClick(screen.getByRole('row', { name: /Abe A\./ }))
    expect(props.onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }))

    await user.click(screen.getByRole('button', { name: /^Bea B\./ }))
    expect(props.onOpen).toHaveBeenLastCalledWith(expect.objectContaining({ id: 'b' }))
  })

  it('can be operated by keyboard: Tab to a client name and press Enter', async () => {
    const { props, user } = setup()
    screen.getByRole('button', { name: /^Abe A\./ }).focus()
    await user.keyboard('{Enter}')
    expect(props.onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }))
  })

  it('sorts by the column that was clicked and announces the current sort', async () => {
    const { props, user } = setup({ sort: { key: 'name', dir: 'desc' } })
    expect(screen.getByRole('columnheader', { name: /Client/ })).toHaveAttribute('aria-sort', 'descending')
    expect(screen.getByRole('columnheader', { name: /Payor/ })).toHaveAttribute('aria-sort', 'none')

    await user.click(within(screen.getByRole('columnheader', { name: /Authorization/ })).getByRole('button'))
    expect(props.onSort).toHaveBeenCalledWith('deadline')
  })

  it('offers import and archive in each row\'s menu', async () => {
    const { props, user } = setup()
    await user.click(screen.getByRole('button', { name: 'Actions for Abe A.' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Import a report' }))
    expect(props.onImport).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }))

    await user.click(screen.getByRole('button', { name: 'Actions for Bea B.' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Archive' }))
    expect(props.onArchive).toHaveBeenCalledWith(expect.objectContaining({ id: 'b' }))
  })

  it('has a caption for screen readers', () => {
    setup()
    expect(screen.getByRole('table')).toHaveAccessibleName(/Active clients/)
  })
})
