import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, api } from '@/lib/api'
import { Clients } from '@/pages/Clients'
import { client, clientDetail, payors, period, periodCard } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { clients: vi.fn(), payors: vi.fn(), createClient: vi.fn(), archiveClient: vi.fn(), clientDetail: vi.fn() } }
})
const mocked = vi.mocked(api)

const urgent = client({ id: 'u', display_name: 'Ula U.', client_identifier: 'U-1', latest_period: period({ days_until_end: 4 }) })
const later = client({ id: 'l', display_name: 'Abe A.', client_identifier: 'A-1', payor_name: 'Optum', latest_period: period({ days_until_end: 80 }) })
const expired = client({ id: 'x', display_name: 'Max X.', client_identifier: 'X-1', latest_period: period({ days_until_end: -6 }) })

function Where() {
  return <div data-testid="where">{useLocation().pathname}</div>
}

function setup() {
  render(
    <MemoryRouter initialEntries={['/clients']}>
      <Routes>
        <Route path="/clients" element={<Clients />} />
        <Route path="/import" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

const rowNames = () => screen.getAllByRole('row').slice(1).map((row) => within(row).getAllByRole('button')[0].textContent ?? '')

beforeEach(() => {
  vi.clearAllMocks()
  mocked.clients.mockResolvedValue([later, urgent, expired])
  mocked.payors.mockResolvedValue(payors)
})

describe('Clients page', () => {
  it('shows a loading state, then the roster with a count', async () => {
    setup()
    expect(screen.getByLabelText('Loading clients')).toBeInTheDocument()
    expect(await screen.findByText('3 active clients')).toBeInTheDocument()
    expect(screen.queryByLabelText('Loading clients')).not.toBeInTheDocument()
  })

  it('puts the clients who need a reauthorization soonest at the top', async () => {
    setup()
    await screen.findByText('3 active clients')
    expect(rowNames().map((n) => n.slice(0, 6))).toEqual(['Max X.', 'Ula U.', 'Abe A.'])
  })

  it('re-sorts when a column is clicked, and flips on a second click', async () => {
    const user = setup()
    await screen.findByText('3 active clients')
    const nameSort = within(screen.getByRole('columnheader', { name: /Client/ })).getByRole('button')

    await user.click(nameSort)
    expect(rowNames().map((n) => n.slice(0, 6))).toEqual(['Abe A.', 'Max X.', 'Ula U.'])
    await user.click(nameSort)
    expect(rowNames().map((n) => n.slice(0, 6))).toEqual(['Ula U.', 'Max X.', 'Abe A.'])
  })

  it('searches across name, ID, diagnosis and payor, and says how many matched', async () => {
    const user = setup()
    await screen.findByText('3 active clients')
    await user.type(screen.getByLabelText('Search clients'), 'optum')
    expect(screen.getByText('1 of 3 clients')).toBeInTheDocument()
    expect(rowNames()).toHaveLength(1)
    expect(rowNames()[0]).toMatch(/^Abe A\./)

    await user.clear(screen.getByLabelText('Search clients'))
    expect(screen.getByText('3 active clients')).toBeInTheDocument()
  })

  it('says so when nothing matches, and keeps the search box', async () => {
    const user = setup()
    await screen.findByText('3 active clients')
    await user.type(screen.getByLabelText('Search clients'), 'zzz')
    expect(screen.getByText(/No clients match “zzz”/)).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Search clients')).toBeInTheDocument()
  })

  describe('with no clients', () => {
    beforeEach(() => mocked.clients.mockResolvedValue([]))

    it('invites the BCBA to add one or import a report', async () => {
      setup()
      expect(await screen.findByText('No clients yet')).toBeInTheDocument()
      expect(screen.queryByLabelText('Search clients')).not.toBeInTheDocument()
    })

    it('takes them to Import from the empty state', async () => {
      const user = setup()
      await screen.findByText('No clients yet')
      await user.click(screen.getByRole('button', { name: 'Import a report' }))
      expect(screen.getByTestId('where')).toHaveTextContent('/import')
    })
  })

  it('shows a failure with a way to try again', async () => {
    mocked.clients.mockRejectedValueOnce(new ApiError(500, 'Something went wrong on the server.'))
    const user = setup()
    expect(await screen.findByText('Something went wrong on the server.')).toBeInTheDocument()
    mocked.clients.mockResolvedValueOnce([urgent])
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('1 active client')).toBeInTheDocument()
    expect(screen.queryByText('Something went wrong on the server.')).not.toBeInTheDocument()
  })

  it('adds a client and shows them without a reload', async () => {
    const created = client({ id: 'n', display_name: 'Nia N.', client_identifier: 'N-1', latest_period: null, period_count: 0 })
    mocked.createClient.mockResolvedValue(created)
    const user = setup()
    await screen.findByText('3 active clients')

    mocked.clients.mockResolvedValue([later, urgent, expired, created])
    await user.click(screen.getByRole('button', { name: 'Add client' }))
    await user.type(await screen.findByLabelText('Name'), 'Nia N.')
    await user.click(screen.getByRole('combobox', { name: 'Payor' }))
    await user.click(await screen.findByRole('option', { name: 'Aetna' }))
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Add client' }))

    expect(await screen.findByText('4 active clients')).toBeInTheDocument()
    expect(screen.getByText('No reports yet')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('archives only after confirming, and the client leaves the list', async () => {
    mocked.archiveClient.mockResolvedValue({ ok: true })
    const user = setup()
    await screen.findByText('3 active clients')

    await user.click(screen.getByRole('button', { name: 'Actions for Ula U.' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Archive' }))
    expect(mocked.archiveClient).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { name: 'Archive Ula U.?' })).toBeInTheDocument()

    mocked.clients.mockResolvedValue([later, expired])
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Archive' }))
    expect(mocked.archiveClient).toHaveBeenCalledWith('u')
    expect(await screen.findByText('2 active clients')).toBeInTheDocument()
    expect(screen.queryByText('Ula U.')).not.toBeInTheDocument()
  })

  it('opens a client\'s details on double-click', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ ...urgent, periods: [periodCard({ period_start: '2026-01-01', period_end: '2026-06-30' })] }))
    const user = setup()
    await screen.findByText('3 active clients')
    await user.dblClick(screen.getByRole('row', { name: /Ula U\./ }))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByRole('heading', { name: 'Ula U.' })).toBeInTheDocument()
    expect(await within(dialog).findByText(/Jan 1, 2026 to Jun 30, 2026/)).toBeInTheDocument()
    expect(mocked.clientDetail).toHaveBeenCalledWith('u')
  })

  it('archiving from the details closes them and asks to confirm', async () => {
    mocked.clientDetail.mockResolvedValue(clientDetail({ ...urgent }))
    const user = setup()
    await screen.findByText('3 active clients')
    await user.dblClick(screen.getByRole('row', { name: /Ula U\./ }))
    await user.click(await screen.findByRole('button', { name: 'Archive client' }))
    expect(await screen.findByRole('heading', { name: 'Archive Ula U.?' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Ula U.' })).not.toBeInTheDocument()
  })

  it('takes the BCBA to Import from a row\'s menu', async () => {
    const user = setup()
    await screen.findByText('3 active clients')
    await user.click(screen.getByRole('button', { name: 'Actions for Abe A.' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Import a report' }))
    expect(screen.getByTestId('where')).toHaveTextContent('/import')
  })
})

describe('Clients page when the API is down', () => {
  it('says the server cannot be reached and offers to retry', async () => {
    const { UNREACHABLE } = await import('@/lib/api')
    mocked.clients.mockRejectedValueOnce(new ApiError(0, UNREACHABLE))
    const user = setup()
    expect(await screen.findByText(UNREACHABLE)).toBeInTheDocument()
    expect(screen.queryByText(/Failed to fetch/)).not.toBeInTheDocument()

    mocked.clients.mockResolvedValueOnce([client()])
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('1 active client')).toBeInTheDocument()
  })
})
