import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AUTOSAVE_MS, useAutosave } from '@/hooks/useAutosave'
import { ApiError, api } from '@/lib/api'
import type { SavedData } from '@/lib/types'
import { clinicalData, validation } from '@/test/fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/lib/api')>()
  return { ...original, api: { saveData: vi.fn() } }
})
const saveData = vi.mocked(api.saveData)

const reply = (): SavedData => ({ data: clinicalData(), validation: validation(), narrative_stale: false })
const initial = clinicalData()

function setup(onSaved = vi.fn()) {
  const hook = renderHook(() => useAutosave(initial, (d) => api.saveData('p1', d), onSaved))
  return { ...hook, onSaved }
}
const setBcba = (name: string) => (draft: { client: { supervising_bcba: string | null } }) => void (draft.client.supervising_bcba = name)

beforeEach(() => {
  vi.useFakeTimers()
  saveData.mockReset()
  saveData.mockResolvedValue(reply())
})
afterEach(() => vi.useRealTimers())

describe('useAutosave', () => {
  it('starts out saved, and saves a moment after an edit', async () => {
    const { result, onSaved } = setup()
    expect(result.current.state).toBe('saved')

    act(() => result.current.update(setBcba('Dr. New')))
    expect(result.current.state).toBe('dirty')
    expect(saveData).not.toHaveBeenCalled()

    await act(() => vi.advanceTimersByTimeAsync(AUTOSAVE_MS))
    expect(saveData).toHaveBeenCalledTimes(1)
    expect(saveData.mock.calls[0][1].client.supervising_bcba).toBe('Dr. New')
    expect(result.current.state).toBe('saved')
    expect(onSaved).toHaveBeenCalledTimes(1)
  })

  it('sends one save with the final value for a burst of typing', async () => {
    const { result } = setup()
    for (const text of ['D', 'Dr', 'Dr.']) {
      act(() => result.current.update(setBcba(text)))
      await act(() => vi.advanceTimersByTimeAsync(AUTOSAVE_MS / 4))
    }
    await act(() => vi.advanceTimersByTimeAsync(AUTOSAVE_MS))
    expect(saveData).toHaveBeenCalledTimes(1)
    expect(saveData.mock.calls[0][1].client.supervising_bcba).toBe('Dr.')
  })

  it('sends edits made during a save right after it, so none are lost', async () => {
    let finishFirst!: (value: SavedData) => void
    saveData.mockImplementationOnce(() => new Promise((resolve) => (finishFirst = resolve)))
    const { result } = setup()

    act(() => result.current.update(setBcba('first')))
    await act(() => vi.advanceTimersByTimeAsync(AUTOSAVE_MS))
    expect(result.current.state).toBe('saving')

    act(() => result.current.update(setBcba('second')))
    await act(async () => finishFirst(reply()))
    await act(() => vi.advanceTimersByTimeAsync(0))

    expect(saveData).toHaveBeenCalledTimes(2)
    expect(saveData.mock.calls[1][1].client.supervising_bcba).toBe('second')
    expect(result.current.state).toBe('saved')
  })

  it('keeps the edits and says why when a save is refused, then recovers', async () => {
    saveData.mockRejectedValueOnce(new ApiError(422, 'current_accuracy_pct: must be at most 100'))
    const { result } = setup()

    act(() => result.current.update(setBcba('Dr. New')))
    await act(() => vi.advanceTimersByTimeAsync(AUTOSAVE_MS))

    expect(result.current.state).toBe('error')
    expect(result.current.error).toContain('must be at most 100')
    expect(result.current.value.client.supervising_bcba).toBe('Dr. New') // still on screen

    await act(() => result.current.saveNow())
    expect(result.current.state).toBe('saved')
    expect(result.current.error).toBeNull()
  })

  it('saves what is pending when the page is left', async () => {
    const { result, unmount } = setup()
    act(() => result.current.update(setBcba('Dr. Last')))
    unmount()
    await vi.advanceTimersByTimeAsync(0)
    expect(saveData).toHaveBeenCalledTimes(1)
    expect(saveData.mock.calls[0][1].client.supervising_bcba).toBe('Dr. Last')
  })

  it('does not save when nothing was edited', async () => {
    const { unmount } = setup()
    unmount()
    await vi.advanceTimersByTimeAsync(AUTOSAVE_MS * 2)
    expect(saveData).not.toHaveBeenCalled()
  })

  it('warns before the tab is closed while changes are unsaved, and only then', async () => {
    const { result } = setup()
    const event = () => {
      const e = new Event('beforeunload', { cancelable: true })
      window.dispatchEvent(e)
      return e.defaultPrevented
    }
    expect(event()).toBe(false)
    act(() => result.current.update(setBcba('x')))
    expect(event()).toBe(true)
    await act(() => vi.advanceTimersByTimeAsync(AUTOSAVE_MS))
    expect(event()).toBe(false)
  })

  it('forgets unsaved edits when asked, and does not send them later', async () => {
    const { result, unmount } = setup()
    act(() => result.current.update(setBcba('Replaced soon')))
    act(() => result.current.discard())
    expect(result.current.state).toBe('saved')
    await vi.advanceTimersByTimeAsync(AUTOSAVE_MS * 2)
    unmount()
    await vi.advanceTimersByTimeAsync(0)
    expect(saveData).not.toHaveBeenCalled()
  })

  it('replace() swaps in whole new data and saves it', async () => {
    const { result } = setup()
    const next = clinicalData({ clinical_justification_for_hours: 'From JSON' })
    act(() => result.current.replace(next))
    await act(() => vi.advanceTimersByTimeAsync(AUTOSAVE_MS))
    expect(saveData.mock.calls[0][1].clinical_justification_for_hours).toBe('From JSON')
  })
})
