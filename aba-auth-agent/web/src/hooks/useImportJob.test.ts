import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { currentStep, POLL_MS, STEPS, STORAGE_KEY, useImportJob } from '@/hooks/useImportJob'
import { api } from '@/lib/api'
import { job } from '@/test/fixtures'

vi.mock('@/lib/api', () => ({
  api: { startImport: vi.fn(), getImport: vi.fn(), answerImport: vi.fn() },
}))
const mocked = vi.mocked(api)
const file = new File(['x'], 'report.docx')

async function tick() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(POLL_MS)
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  sessionStorage.clear()
})

describe('useImportJob', () => {
  it('starts a job and polls until it is done, then stops asking', async () => {
    mocked.startImport.mockResolvedValue(job('reading'))
    mocked.getImport.mockResolvedValueOnce(job('drafting')).mockResolvedValueOnce(job('done'))
    const { result } = renderHook(() => useImportJob())

    await act(async () => void (await result.current.start(file)))
    expect(result.current.job?.stage).toBe('reading')

    await tick()
    expect(result.current.job?.stage).toBe('drafting')
    await tick()
    expect(result.current.job?.stage).toBe('done')

    await tick()
    await tick()
    expect(mocked.getImport).toHaveBeenCalledTimes(2) // no polling once finished
  })

  it('stops polling when the report needs answers, and resumes after they are sent', async () => {
    mocked.startImport.mockResolvedValue(job('reading'))
    mocked.getImport.mockResolvedValueOnce(job('needs_answers', { questions: ['client'] }))
    mocked.answerImport.mockResolvedValue(job('setting_up'))
    mocked.getImport.mockResolvedValueOnce(job('done'))
    const { result } = renderHook(() => useImportJob())

    await act(async () => void (await result.current.start(file)))
    await tick()
    expect(result.current.job?.stage).toBe('needs_answers')
    await tick()
    expect(mocked.getImport).toHaveBeenCalledTimes(1) // waiting on the BCBA, not the server

    await act(async () => void (await result.current.answer({ new_identifier: 'HB-9' })))
    expect(mocked.answerImport).toHaveBeenCalledWith('job1', { new_identifier: 'HB-9' })
    await tick()
    expect(result.current.job?.stage).toBe('done')
  })

  it('shows why an upload was refused and stays ready for another file', async () => {
    mocked.startImport.mockRejectedValue(new Error('Upload a PDF or Word (.docx) report.'))
    const { result } = renderHook(() => useImportJob())
    await act(async () => void (await result.current.start(file)))
    expect(result.current.error).toBe('Upload a PDF or Word (.docx) report.')
    expect(result.current.job).toBeNull()
    expect(result.current.busy).toBe(false)
  })

  it('keeps the form open and shows the reason when answers are refused', async () => {
    mocked.startImport.mockResolvedValue(job('needs_answers', { questions: ['period'] }))
    mocked.answerImport.mockRejectedValue(new Error('The period must end after it starts.'))
    const { result } = renderHook(() => useImportJob())
    await act(async () => void (await result.current.start(file)))
    await act(async () => void (await result.current.answer({})))
    expect(result.current.error).toBe('The period must end after it starts.')
    expect(result.current.job?.stage).toBe('needs_answers')
  })

  it('surfaces a polling failure, such as the server forgetting the import', async () => {
    mocked.startImport.mockResolvedValue(job('reading'))
    mocked.getImport.mockRejectedValue(new Error('Import not found.'))
    const { result } = renderHook(() => useImportJob())
    await act(async () => void (await result.current.start(file)))
    await tick()
    expect(result.current.error).toBe('Import not found.')
  })

  it('reset clears the job and the error', async () => {
    mocked.startImport.mockResolvedValue(job('done'))
    const { result } = renderHook(() => useImportJob())
    await act(async () => void (await result.current.start(file)))
    act(() => result.current.reset())
    expect(result.current.job).toBeNull()
    expect(result.current.error).toBeNull()
  })
})

describe('resuming after a refresh', () => {
  it('picks up the import that was running', async () => {
    sessionStorage.setItem(STORAGE_KEY, 'job1')
    mocked.getImport.mockResolvedValue(job('drafting'))
    const { result } = renderHook(() => useImportJob())
    await act(async () => {})
    expect(mocked.getImport).toHaveBeenCalledWith('job1')
    expect(result.current.job?.stage).toBe('drafting')
  })

  it('forgets an import the server no longer knows about', async () => {
    sessionStorage.setItem(STORAGE_KEY, 'gone')
    mocked.getImport.mockRejectedValue(new Error('Import not found.'))
    const { result } = renderHook(() => useImportJob())
    await act(async () => {})
    expect(result.current.job).toBeNull()
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull()
  })

  it('remembers a new import, and forgets it on reset', async () => {
    mocked.startImport.mockResolvedValue(job('reading'))
    const { result } = renderHook(() => useImportJob())
    await act(async () => void (await result.current.start(file)))
    expect(sessionStorage.getItem(STORAGE_KEY)).toBe('job1')
    act(() => result.current.reset())
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull()
  })

  it('starts empty when nothing was running', async () => {
    const { result } = renderHook(() => useImportJob())
    await act(async () => {})
    expect(mocked.getImport).not.toHaveBeenCalled()
    expect(result.current.job).toBeNull()
  })
})

describe('currentStep', () => {
  it('maps each stage to the step in progress', () => {
    expect(currentStep('reading')).toBe(0)
    expect(currentStep('setting_up')).toBe(1)
    expect(currentStep('drafting')).toBe(2)
    expect(currentStep('checking')).toBe(3)
    expect(currentStep('done')).toBe(STEPS.length)
  })

  it('treats a report waiting for answers as read but not yet set up', () => {
    expect(currentStep('needs_answers')).toBe(1)
  })
})
