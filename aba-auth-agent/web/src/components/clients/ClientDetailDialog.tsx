import { useEffect, useState } from 'react'

import { NewPeriodForm } from '@/components/clients/NewPeriodForm'
import { PeriodCardView } from '@/components/clients/PeriodCardView'
import { TrendsTable } from '@/components/clients/TrendsTable'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/deadlines'
import type { Client, ClientDetail, PeriodCard } from '@/lib/types'

export function ClientDetailDialog({
  client,
  onClose,
  onImport,
  onArchive,
  onChanged,
}: {
  /** The client to show; null keeps the dialog closed. */
  client: Client | null
  onClose: () => void
  onImport: (client: Client) => void
  onArchive: (client: Client) => void
  /** Called when something here changes what the roster shows (a new period). */
  onChanged?: () => void
}) {
  const [detail, setDetail] = useState<ClientDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [justAdded, setJustAdded] = useState<string | null>(null)
  const id = client?.id

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setDetail(null)
    setError(null)
    setJustAdded(null)
    api
      .clientDetail(id)
      .then((loaded) => !cancelled && setDetail(loaded))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : 'Could not load this client.'))
    return () => {
      cancelled = true
    }
  }, [id])

  const added = (period: PeriodCard) => {
    // newest period first, like the server's list
    setDetail((current) =>
      current && { ...current, period_count: current.period_count + 1, periods: [period, ...current.periods].sort((a, b) => b.period_end.localeCompare(a.period_end)) },
    )
    setJustAdded(period.id)
    onChanged?.()
  }

  return (
    <Dialog open={client !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{client?.display_name}</DialogTitle>
          <DialogDescription>
            {client?.client_identifier ?? 'No client ID'} · {client?.payor_name}
          </DialogDescription>
        </DialogHeader>

        {client && client.diagnosis_codes.length > 0 && (
          <div className="flex flex-wrap gap-1.5" aria-label="Diagnosis codes">
            {client.diagnosis_codes.map((code) => (
              <Badge key={code} variant="secondary">
                {code}
              </Badge>
            ))}
          </div>
        )}

        <div className="grid gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-medium">Authorization periods</h3>
            {client && <NewPeriodForm clientId={client.id} onCreated={added} />}
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {!error && !detail && <Skeleton className="h-24 w-full" aria-label="Loading periods" />}
          {detail && detail.periods.length === 0 && (
            <p className="text-sm text-muted-foreground">No reports imported yet for this client.</p>
          )}
          {detail && detail.periods.length > 0 && (
            <Accordion
              key={detail.periods.length /* a new period opens on its own */}
              type="single"
              collapsible
              defaultValue={justAdded ?? detail.periods[0].id}
              className="rounded-md border"
            >
              {detail.periods.map((period) => (
                <AccordionItem key={period.id} value={period.id} className="px-4">
                  <AccordionTrigger>
                    {formatDate(period.period_start)} to {formatDate(period.period_end)}
                  </AccordionTrigger>
                  <AccordionContent>
                    <PeriodCardView period={period} />
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          )}
        </div>

        {detail?.trends && <TrendsTable trends={detail.trends} />}

        <DialogFooter className="sm:justify-between">
          <Button variant="outline" onClick={() => client && onArchive(client)}>
            Archive client
          </Button>
          <Button onClick={() => client && onImport(client)}>Import a report</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
