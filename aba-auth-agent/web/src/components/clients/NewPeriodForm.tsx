import { Plus } from 'lucide-react'
import { useState } from 'react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import type { PeriodCard } from '@/lib/types'

/** Authorizations usually run about six months. */
export const DEFAULT_PERIOD_DAYS = 182

const isoDay = (date: Date) => {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}
export const defaultDates = (today = new Date()) => {
  const end = new Date(today)
  end.setDate(end.getDate() + DEFAULT_PERIOD_DAYS)
  return { start: isoDay(today), end: isoDay(end) }
}

export function NewPeriodForm({ clientId, onCreated }: { clientId: string; onCreated: (period: PeriodCard) => void }) {
  const [open, setOpen] = useState(false)
  const [dates, setDates] = useState(defaultDates)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Plus /> New authorization period
      </Button>
    )
  }

  async function create() {
    if (!dates.start || !dates.end) return setError('Enter both dates.')
    if (dates.end <= dates.start) return setError('The period must end after it starts.')
    setBusy(true)
    setError(null)
    try {
      onCreated(await api.createPeriod(clientId, dates.start, dates.end))
      setOpen(false)
      setDates(defaultDates())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create the period.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form
      className="grid gap-3 rounded-md border p-3"
      onSubmit={(e) => {
        e.preventDefault()
        void create()
      }}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label htmlFor="period-start">Period start</Label>
          <Input id="period-start" type="date" value={dates.start} onChange={(e) => setDates({ ...dates, start: e.target.value })} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="period-end">Period end</Label>
          <Input id="period-end" type="date" value={dates.end} onChange={(e) => setDates({ ...dates, end: e.target.value })} />
        </div>
      </div>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={busy}>
          Create period
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </form>
  )
}
