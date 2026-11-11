import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ArchiveClientDialog } from '@/components/clients/ArchiveClientDialog'
import { ApiError, api } from '@/lib/api'
import { client } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { archiveClient: vi.fn() } }
})
const mocked = vi.mocked(api)
beforeEach(() => vi.clearAllMocks())

function setup(target = client()) {
  const onClose = vi.fn()
  const onArchived = vi.fn()
  render(<ArchiveClientDialog client={target} onClose={onClose} onArchived={onArchived} />)
  return { onClose, onArchived, user: userEvent.setup() }
}

describe('ArchiveClientDialog', () => {
  it('says who is being archived and that their records are kept', () => {
    setup()
    expect(screen.getByRole('heading', { name: 'Archive Sam W.?' })).toBeInTheDocument()
    expect(screen.getByText(/reports and drafts are kept/)).toBeInTheDocument()
  })

  it('archives only after confirming, then closes', async () => {
    mocked.archiveClient.mockResolvedValue({ ok: true })
    const { user, onArchived, onClose } = setup()
    expect(mocked.archiveClient).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Archive' }))
    expect(mocked.archiveClient).toHaveBeenCalledWith('c1')
    expect(onArchived).toHaveBeenCalledWith(expect.objectContaining({ id: 'c1' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('cancel changes nothing', async () => {
    const { user, onClose, onArchived } = setup()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onClose).toHaveBeenCalled()
    expect(mocked.archiveClient).not.toHaveBeenCalled()
    expect(onArchived).not.toHaveBeenCalled()
  })

  it('shows why it failed and stays open', async () => {
    mocked.archiveClient.mockRejectedValue(new ApiError(404, 'Client not found.'))
    const { user, onClose, onArchived } = setup()
    await user.click(screen.getByRole('button', { name: 'Archive' }))
    expect(await screen.findByText('Client not found.')).toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
    expect(onArchived).not.toHaveBeenCalled()
  })

  it('renders nothing when there is no client', () => {
    render(<ArchiveClientDialog client={null} onClose={vi.fn()} onArchived={vi.fn()} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
