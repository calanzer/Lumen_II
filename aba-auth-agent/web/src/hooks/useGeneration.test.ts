import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { POLL_MS, useGeneration } from '@/hooks/useGeneration'
import { ApiError, api } from '@/lib/api'
import { generation } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { generation: vi.fn(), startGeneration: vi.fn() } }
})
const mocked = vi.mocked(api)

const tick = (ms = POLL_MS) => act(() => vi.advanceTimersByTimeAsync(ms))

beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  mocked.generation.mockResolvedValue(generation())
})
afterEach(() => vi.useRealTimers())

async function setup() {
  const onFinished = vi.fn()
  const hook = renderHook(() => useGeneration('p1', onFinished))
  await tick(0)
  return { ...hook, onFinished }
}

describe('useGeneration', () => {
  it('starts idle and does nothing until asked', async () => {
    const { result, onFinished } = await setup()
    expect(result.current.status.stage).toBe('idle')
    expect(result.current.working).toBe(false)
    await tick(POLL_MS * 3)
    expect(mocked.generation).toHaveBeenCalledTimes(1) // only the look-on-arrival
    expect(onFinished).not.toHaveBeenCalled()
  })

  it('follows a job from start to finish and then says it is finished, once', async () => {
    mocked.startGeneration.mockResolvedValue(generation({ stage: 'drafting' }))
    mocked.generation
      .mockResolvedValueOnce(generation()) // on arrival
      .mockResolvedValueOnce(generation({ stage: 'checking' }))
      .mockResolvedValue(generation({ stage: 'done', discrepancies: ['x'] }))
    const { result, onFinished } = await setup()

    await act(() => result.current.start())
    expect(result.current.working).toBe(true)

    await tick()
    expect(result.current.status.stage).toBe('checking')
    expect(onFinished).not.toHaveBeenCalled()

    await tick()
    expect(result.current.status).toMatchObject({ stage: 'done', discrepancies: ['x'] })
    expect(result.current.working).toBe(false)
    expect(onFinished).toHaveBeenCalledTimes(1)

    await tick(POLL_MS * 3) // and it stops asking
    expect(onFinished).toHaveBeenCalledTimes(1)
    expect(mocked.generation).toHaveBeenCalledTimes(3)
  })

  it('a failed job is reported as finished too, so the screen can reload', async () => {
    mocked.startGeneration.mockResolvedValue(generation({ stage: 'drafting' }))
    mocked.generation.mockResolvedValueOnce(generation()).mockResolvedValue(generation({ stage: 'error', error: 'model overloaded' }))
    const { result, onFinished } = await setup()
    await act(() => result.current.start())
    await tick()
    expect(result.current.status).toMatchObject({ stage: 'error', error: 'model overloaded' })
    expect(onFinished).toHaveBeenCalledTimes(1)
  })

  it('picks up a job already running when the page opens', async () => {
    mocked.generation.mockResolvedValueOnce(generation({ stage: 'drafting' })).mockResolvedValue(generation({ stage: 'done', discrepancies: [] }))
    const { result, onFinished } = await setup()
    expect(result.current.working).toBe(true)
    await tick()
    expect(result.current.status.stage).toBe('done')
    expect(onFinished).toHaveBeenCalledTimes(1)
  })

  it('does not replay a job that finished before the page opened', async () => {
    mocked.generation.mockResolvedValue(generation({ stage: 'done', discrepancies: ['old news'] }))
    const { result, onFinished } = await setup()
    expect(result.current.status.stage).toBe('idle')
    expect(onFinished).not.toHaveBeenCalled()
  })

  it('says why when a job cannot be started', async () => {
    mocked.startGeneration.mockRejectedValue(new ApiError(409, 'A narrative is already being written for this period.'))
    const { result } = await setup()
    await act(() => result.current.start())
    expect(result.current.error).toBe('A narrative is already being written for this period.')
    expect(result.current.working).toBe(false)
  })

  it('says so when it loses track of a running job', async () => {
    mocked.startGeneration.mockResolvedValue(generation({ stage: 'drafting' }))
    mocked.generation.mockResolvedValueOnce(generation()).mockRejectedValue(new ApiError(0, "Can't reach the server."))
    const { result } = await setup()
    await act(() => result.current.start())
    await tick()
    expect(result.current.error).toBe("Can't reach the server.")
  })
})
