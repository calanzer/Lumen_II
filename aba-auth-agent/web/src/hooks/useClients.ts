import { useCallback, useEffect, useState } from 'react'

import { api } from '@/lib/api'
import type { Client } from '@/lib/types'

export function useClients() {
  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setClients(await api.clients())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load clients.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { clients, loading, error, reload }
}
