import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { ApiError, api, UNREACHABLE } from '@/lib/api'
import { lastPeriod } from '@/hooks/usePeriod'
import { generation, payors, periodDetail } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { me: vi.fn(), login: vi.fn(), logout: vi.fn(), payors: vi.fn(), clients: vi.fn(), period: vi.fn(), template: vi.fn(), generation: vi.fn() } }
})
const mocked = vi.mocked(api)

beforeEach(() => {
  vi.clearAllMocks()
  mocked.clients.mockResolvedValue([])
  window.history.pushState({}, '', '/')
})

describe('App', () => {
  it('sends a signed-out visitor to the login screen', async () => {
    mocked.me.mockRejectedValue(new ApiError(401, 'Not signed in.'))
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })

  it('shows the reason when a sign-in is refused, and lets the BCBA in once it works', async () => {
    mocked.me.mockRejectedValue(new ApiError(401, 'Not signed in.'))
    mocked.login.mockRejectedValueOnce(new ApiError(401, 'Username or password is incorrect.'))
    mocked.login.mockResolvedValueOnce({ username: 'bcba', name: 'Test BCBA' })
    const user = userEvent.setup()
    render(<App />)

    await user.type(await screen.findByLabelText('Username'), 'bcba')
    await user.type(screen.getByLabelText('Password'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Username or password is incorrect.')).toBeInTheDocument()

    await user.clear(screen.getByLabelText('Password'))
    await user.type(screen.getByLabelText('Password'), 'right')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Import a report' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/import')
  })

  it('shows the app to a signed-in user and lands on Import', async () => {
    mocked.me.mockResolvedValue({ username: 'bcba', name: 'Test BCBA' })
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Import a report' })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Main' })
    expect(nav).toHaveTextContent('Import')
    expect(nav).toHaveTextContent('Templates')
  })

  it('shows the Templates screen at /templates', async () => {
    mocked.me.mockResolvedValue({ username: 'bcba', name: 'Test BCBA' })
    mocked.payors.mockResolvedValue(payors)
    mocked.template.mockResolvedValue({ payor: 'aetna', payor_name: 'Aetna', active: null, default_sections: ['Client Overview'] })
    window.history.pushState({}, '', '/templates')
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Templates' })).toBeInTheDocument()
    expect(await screen.findByText('Using the built-in default layout')).toBeInTheDocument()
  })

  it('opens a period at its Review, Generate and Export addresses', async () => {
    mocked.me.mockResolvedValue({ username: 'bcba', name: 'Test BCBA' })
    mocked.period.mockResolvedValue(periodDetail())
    window.history.pushState({}, '', '/periods/p1/review')
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Sam W.' })).toBeInTheDocument()
    expect(screen.getByLabelText('Client ID')).toHaveValue('HB-1')
  })

  it('the sidebar steps go to the period you worked on last, or ask you to choose a client', async () => {
    mocked.me.mockResolvedValue({ username: 'bcba', name: 'Test BCBA' })
    mocked.period.mockResolvedValue(periodDetail())
    mocked.generation.mockResolvedValue(generation())

    lastPeriod.clear()
    window.history.pushState({}, '', '/review')
    const first = render(<App />)
    expect(await screen.findByText('Choose a client first')).toBeInTheDocument()
    first.unmount()

    lastPeriod.set('p1')
    window.history.pushState({}, '', '/generate')
    render(<App />)
    await waitFor(() => expect(window.location.pathname).toBe('/periods/p1/generate'))
    expect(await screen.findByRole('heading', { name: 'Sam W.' })).toBeInTheDocument()
    lastPeriod.clear()
  })

  it('shows the Clients screen at /clients', async () => {
    mocked.me.mockResolvedValue({ username: 'bcba', name: 'Test BCBA' })
    window.history.pushState({}, '', '/clients')
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Clients' })).toBeInTheDocument()
    expect(await screen.findByText('No clients yet')).toBeInTheDocument()
  })

  it('goes straight in when sign-in is skipped locally, and says so', async () => {
    mocked.me.mockResolvedValue({ username: 'local', name: 'Local tester', local: true })
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Import a report' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/import')
    expect(screen.getAllByText('Local').length).toBeGreaterThan(0)

    await user.click(screen.getAllByRole('button', { name: /Local tester/ })[0])
    expect(await screen.findByText(/Sign-in is skipped/)).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: /Sign out/ })).not.toBeInTheDocument() // nothing to sign out of
  })

  it('says the server is down instead of showing a login form, and recovers on retry', async () => {
    mocked.me.mockRejectedValueOnce(new ApiError(0, UNREACHABLE))
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByText("Can't reach Lumen ABA")).toBeInTheDocument()
    expect(screen.getByText(UNREACHABLE)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sign in' })).not.toBeInTheDocument()
    expect(window.location.pathname).not.toBe('/login')

    mocked.me.mockResolvedValueOnce({ username: 'bcba', name: 'Test BCBA' })
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { name: 'Import a report' })).toBeInTheDocument()
  })

  it('treats a server error the same way, not as being signed out', async () => {
    mocked.me.mockRejectedValue(new ApiError(500, 'Something went wrong on the server.'))
    render(<App />)
    expect(await screen.findByText("Can't reach Lumen ABA")).toBeInTheDocument()
    expect(screen.getByText('Something went wrong on the server.')).toBeInTheDocument()
  })

  it('signs out', async () => {
    mocked.me.mockResolvedValue({ username: 'bcba', name: 'Test BCBA' })
    mocked.logout.mockResolvedValue({ ok: true })
    const user = userEvent.setup()
    render(<App />)
    await screen.findByRole('heading', { name: 'Import a report' })

    await user.click(screen.getAllByRole('button', { name: /Test BCBA|T/ })[0])
    await user.click(await screen.findByRole('menuitem', { name: /Sign out/ }))

    await waitFor(() => expect(window.location.pathname).toBe('/login'))
    expect(mocked.logout).toHaveBeenCalled()
  })
})
