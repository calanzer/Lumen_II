import { deadlineTone } from '@/lib/deadlines'
import type { Client } from '@/lib/types'

export type SortKey = 'name' | 'payor' | 'deadline'
export type SortDir = 'asc' | 'desc'
export interface Sort {
  key: SortKey
  dir: SortDir
}

/** What a search matches against: name, client ID, diagnosis codes and payor. */
function haystack(client: Client): string {
  return [client.display_name, client.client_identifier ?? '', client.diagnosis_codes.join(' '), client.payor_name]
    .join(' ')
    .toLowerCase()
}

/** Every word typed has to appear somewhere, in any order. */
export function filterClients(clients: Client[], query: string): Client[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (words.length === 0) return clients
  return clients.filter((client) => {
    const text = haystack(client)
    return words.every((word) => text.includes(word))
  })
}

const byName = (a: Client, b: Client) => a.display_name.localeCompare(b.display_name, undefined, { numeric: true, sensitivity: 'base' })

/** Days until the authorization to act on, or Infinity when there is nothing to act on. */
function urgency(client: Client): number {
  const period = client.latest_period
  if (!period || deadlineTone(period) === 'done') return Number.POSITIVE_INFINITY
  return period.days_until_end
}

const COMPARE: Record<SortKey, (a: Client, b: Client) => number> = {
  name: byName,
  payor: (a, b) => a.payor_name.localeCompare(b.payor_name) || byName(a, b),
  // Most urgent first (expired, then soonest). Finished or empty clients go last, whatever the direction.
  deadline: (a, b) => {
    const x = urgency(a)
    const y = urgency(b)
    if (x === y) return byName(a, b)
    return x < y ? -1 : 1
  },
}

export function sortClients(clients: Client[], { key, dir }: Sort): Client[] {
  const sorted = [...clients].sort(COMPARE[key])
  if (dir === 'asc') return sorted
  if (key !== 'deadline') return sorted.reverse()
  // Reversing the deadline order would put clients with nothing to act on first; keep them last.
  const live = sorted.filter((c) => urgency(c) !== Number.POSITIVE_INFINITY).reverse()
  return [...live, ...sorted.filter((c) => urgency(c) === Number.POSITIVE_INFINITY)]
}

/** Click a column: sort by it ascending, or flip direction if it is already the sort. */
export function nextSort(current: Sort, key: SortKey): Sort {
  return current.key === key ? { key, dir: current.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }
}
