import { useEffect, useState } from 'react'

import { api } from '@/lib/api'
import type { Client, Payor } from '@/lib/types'

/** Payors and the client roster, loaded when `enabled` first becomes true. */
export function useReference(enabled: boolean) {
  const [payors, setPayors] = useState<Payor[]>([])
  const [clients, setClients] = useState<Client[]>([])

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    Promise.all([api.payors(), api.clients()])
      .then(([loadedPayors, loadedClients]) => {
        if (cancelled) return
        setPayors(loadedPayors)
        setClients(loadedClients)
      })
      .catch(console.error)
    return () => {
      cancelled = true
    }
  }, [enabled])

  return { payors, clients }
}
