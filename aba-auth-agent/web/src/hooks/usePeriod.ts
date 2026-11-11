import { useCallback, useEffect, useState } from 'react'

import { api } from '@/lib/api'
import type { PeriodDetail } from '@/lib/types'

const LAST_PERIOD_KEY = 'lumen.lastPeriod'

/** The period the BCBA last opened, so the sidebar's Review / Generate / Export links know where to go. */
export const lastPeriod = {
  get(): string | null {
    try {
      return localStorage.getItem(LAST_PERIOD_KEY)
    } catch {
      return null
    }
  },
  set(id: string) {
    try {
      localStorage.setItem(LAST_PERIOD_KEY, id)
    } catch {
      // storage unavailable: the links just won't remember
    }
  },
  clear() {
    try {
      localStorage.removeItem(LAST_PERIOD_KEY)
    } catch {
      // nothing to clear
    }
  },
}

export function usePeriod(periodId: string | undefined) {
  const [period, setPeriod] = useState<PeriodDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!periodId) return
    try {
      setPeriod(await api.period(periodId))
      setError(null)
      lastPeriod.set(periodId)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load this period.')
    }
  }, [periodId])

  useEffect(() => {
    setPeriod(null)
    setError(null)
    void reload()
  }, [reload])

  return { period, setPeriod, error, reload }
}
