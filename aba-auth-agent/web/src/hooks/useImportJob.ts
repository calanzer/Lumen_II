import { useCallback, useEffect, useState } from 'react'

import { api } from '@/lib/api'
import type { Answers, ImportJob, Stage } from '@/lib/types'

/** Stages in which the server is still working, so we keep asking how it's going. */
const WORKING: ReadonlySet<Stage> = new Set(['reading', 'setting_up', 'drafting', 'checking'])
export const POLL_MS = 1500
export const STORAGE_KEY = 'lumen.importJob'

export const STEPS: { stage: Stage; label: string }[] = [
  { stage: 'reading', label: 'Reading the report' },
  { stage: 'setting_up', label: 'Saving the client and period' },
  { stage: 'drafting', label: 'Drafting the narrative' },
  { stage: 'checking', label: 'Cross-checking the numbers' },
]

const message = (error: unknown) => (error instanceof Error ? error.message : 'Something went wrong.')

// Remembering the job id lets a refresh pick the import back up instead of losing it.
const remember = (id: string | null) => {
  try {
    if (id) sessionStorage.setItem(STORAGE_KEY, id)
    else sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // storage unavailable (private mode): resuming just won't work
  }
}
const remembered = () => {
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function useImportJob() {
  const [job, setJob] = useState<ImportJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // After a refresh, pick up the import that was in progress.
  useEffect(() => {
    const id = remembered()
    if (!id) return
    api
      .getImport(id)
      .then(setJob)
      .catch(() => remember(null)) // the server forgot it (restart), so start fresh
  }, [])

  useEffect(() => {
    if (job) remember(job.id)
  }, [job])

  // While the server works, check on the job; each answer replaces `job`, which re-runs this.
  useEffect(() => {
    if (!job || !WORKING.has(job.stage)) return
    const timer = setTimeout(async () => {
      try {
        setJob(await api.getImport(job.id))
      } catch (e) {
        setError(message(e))
      }
    }, POLL_MS)
    return () => clearTimeout(timer)
  }, [job])

  const start = useCallback(async (file: File) => {
    setError(null)
    setBusy(true)
    try {
      setJob(await api.startImport(file))
    } catch (e) {
      setError(message(e))
    } finally {
      setBusy(false)
    }
  }, [])

  const answer = useCallback(
    async (answers: Answers) => {
      if (!job) return
      setError(null)
      setBusy(true)
      try {
        setJob(await api.answerImport(job.id, answers))
      } catch (e) {
        setError(message(e)) // e.g. "Enter the authorization period dates."
      } finally {
        setBusy(false)
      }
    },
    [job],
  )

  const reset = useCallback(() => {
    remember(null)
    setJob(null)
    setError(null)
  }, [])

  return { job, error, busy, start, answer, reset }
}

/** Index of the step in progress (STEPS.length once finished), for the progress display. */
export function currentStep(stage: Stage): number {
  if (stage === 'done') return STEPS.length
  if (stage === 'needs_answers') return 1 // reading is finished; setting up is waiting on the BCBA
  const index = STEPS.findIndex((step) => step.stage === stage)
  return index === -1 ? 0 : index
}
