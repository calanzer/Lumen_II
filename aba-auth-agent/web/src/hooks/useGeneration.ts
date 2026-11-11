import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from '@/lib/api'
import type { GenerationStage, GenerationStatus } from '@/lib/types'

export const POLL_MS = 1500
const WORKING: ReadonlySet<GenerationStage> = new Set(['drafting', 'checking'])
const IDLE: GenerationStatus = { stage: 'idle', error: null, discrepancies: null, check_error: null }

export const isWorking = (stage: GenerationStage) => WORKING.has(stage)

/**
 * Starts writing a period's narrative and follows it to the end. A page refresh in the middle
 * picks the same job back up; a job that finished earlier isn't replayed on arrival.
 * `onFinished` runs when a job this page was watching ends, so the new draft can be loaded.
 */
export function useGeneration(periodId: string, onFinished: () => void) {
  const [status, setStatus] = useState<GenerationStatus>(IDLE)
  const [error, setError] = useState<string | null>(null)
  const finished = useRef(onFinished)
  finished.current = onFinished
  const watching = useRef(false) // true once we've seen the job working

  const accept = useCallback((next: GenerationStatus) => {
    if (WORKING.has(next.stage)) watching.current = true
    setStatus(next)
    if (!WORKING.has(next.stage) && watching.current) {
      watching.current = false
      finished.current()
    }
  }, [])

  // Pick up a job that was already running when the page opened.
  useEffect(() => {
    let cancelled = false
    api
      .generation(periodId)
      .then((current) => !cancelled && WORKING.has(current.stage) && accept(current))
      .catch(() => {}) // nothing running that we know of
    return () => {
      cancelled = true
    }
  }, [periodId, accept])

  useEffect(() => {
    if (!WORKING.has(status.stage)) return
    const timer = setTimeout(async () => {
      try {
        accept(await api.generation(periodId))
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Lost track of the draft.')
      }
    }, POLL_MS)
    return () => clearTimeout(timer)
  }, [status, periodId, accept])

  const start = useCallback(async () => {
    setError(null)
    try {
      accept(await api.startGeneration(periodId))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start writing the narrative.')
    }
  }, [periodId, accept])

  return { status, error, start, working: WORKING.has(status.stage) }
}
