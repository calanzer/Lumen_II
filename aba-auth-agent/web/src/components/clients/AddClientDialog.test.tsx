import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AddClientDialog, parseCodes } from '@/components/clients/AddClientDialog'
import { ApiError, api } from '@/lib/api'
import { client, payors } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { createClient: vi.fn() } }
})
const mocked = vi.mocked(api)

function setup() {
  const onOpenChange = vi.fn()
  const onCreated = vi.fn()
  render(<AddClientDialog open onOpenChange={onOpenChange} payors={payors} onCreated={onCreated} />)
  return { onOpenChange, onCreated, user: userEvent.setup() }
}

async function choosePayor(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(screen.getByRole('combobox', { name: 'Payor' }))
  await user.click(await screen.findByRole('option', { name }))
}

beforeEach(() => vi.clearAllMocks())

describe('parseCodes', () => {
  it('splits on commas, semicolons and new lines and drops blanks', () => {
    expect(parseCodes('F84.0, F80.2;  F90 \n, ,')).toEqual(['F84.0', 'F80.2', 'F90'])
    expect(parseCodes('   ')).toEqual([])
  })
})

describe('AddClientDialog', () => {
  it('asks for a name before anything else, without calling the server', async () => {
    const { user } = setup()
    await user.click(screen.getByRole('button', { name: 'Add client' }))
    expect(screen.getByText('Enter a name.')).toBeInTheDocument()
    expect(mocked.createClient).not.toHaveBeenCalled()
  })

  it('then asks for a payor', async () => {
    const { user } = setup()
    await user.type(screen.getByLabelText('Name'), 'Pat')
    await user.click(screen.getByRole('button', { name: 'Add client' }))
    expect(screen.getByText('Choose a payor.')).toBeInTheDocument()
    expect(mocked.createClient).not.toHaveBeenCalled()
  })

  it('sends the tidied client, then closes and reports it', async () => {
    mocked.createClient.mockResolvedValue(client({ id: 'new' }))
    const { user, onCreated, onOpenChange } = setup()
    await user.type(screen.getByLabelText('Name'), 'Martinez, A.')
    await user.type(screen.getByLabelText('Client ID'), 'CR-9')
    await user.type(screen.getByLabelText('Diagnosis codes'), 'F84.0, F80.2')
    await choosePayor(user, 'Aetna')
    await user.click(screen.getByRole('button', { name: 'Add client' }))

    expect(mocked.createClient).toHaveBeenCalledWith({
      display_name: 'Martinez, A.',
      client_identifier: 'CR-9',
      diagnosis_codes: ['F84.0', 'F80.2'],
      payor: 'aetna',
    })
    expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ id: 'new' }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('leaves the client ID out when it was left blank', async () => {
    mocked.createClient.mockResolvedValue(client())
    const { user } = setup()
    await user.type(screen.getByLabelText('Name'), 'Pat')
    await choosePayor(user, 'Optum / UnitedHealthcare')
    await user.click(screen.getByRole('button', { name: 'Add client' }))
    expect(mocked.createClient.mock.calls[0][0]).not.toHaveProperty('client_identifier')
  })

  it("shows the server's reason and stays open when a client is refused", async () => {
    mocked.createClient.mockRejectedValue(new ApiError(409, 'A client with that ID already exists.'))
    const { user, onCreated, onOpenChange } = setup()
    await user.type(screen.getByLabelText('Name'), 'Pat')
    await user.type(screen.getByLabelText('Client ID'), 'CR-1')
    await choosePayor(user, 'Aetna')
    await user.click(screen.getByRole('button', { name: 'Add client' }))

    expect(await screen.findByText('A client with that ID already exists.')).toBeInTheDocument()
    expect(onCreated).not.toHaveBeenCalled()
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
    expect(screen.getByLabelText('Name')).toHaveValue('Pat') // nothing the BCBA typed is lost
  })

  it('cancel closes it', async () => {
    const { user, onOpenChange } = setup()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
