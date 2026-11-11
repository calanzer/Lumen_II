import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { PeriodDetail } from '@/lib/types'

/** Waits for the period to load, and shows a plain explanation when it can't be (or has nothing yet). */
export function PeriodGate({
  period,
  error,
  retry,
  needs,
  children,
}: {
  period: PeriodDetail | null
  error: string | null
  retry: () => void
  /** What the screen needs before it can show anything */
  needs: 'data' | 'narrative'
  children: (period: PeriodDetail) => ReactNode
}) {
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Couldn't open this period</AlertTitle>
        <AlertDescription className="grid gap-3">
          <span>{error}</span>
          <Button variant="outline" size="sm" className="w-fit" onClick={retry}>
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    )
  }
  if (!period) return <Skeleton className="h-48 w-full" aria-label="Loading" />

  if (needs === 'data' && !period.data) {
    return (
      <Alert>
        <AlertTitle>No report has been imported for this period yet</AlertTitle>
        <AlertDescription className="grid gap-3">
          <span>Import a progress report and the data will show up here for review.</span>
          <Button asChild size="sm" className="w-fit">
            <Link to="/import">Import a report</Link>
          </Button>
        </AlertDescription>
      </Alert>
    )
  }
  if (needs === 'narrative' && !period.narrative) {
    return (
      <Alert>
        <AlertTitle>No narrative has been written yet</AlertTitle>
        <AlertDescription className="grid gap-3">
          <span>Generate the narrative first, then come back to export it.</span>
          <Button asChild size="sm" className="w-fit">
            <Link to={`/periods/${period.id}/generate`}>Go to Generate</Link>
          </Button>
        </AlertDescription>
      </Alert>
    )
  }
  return <>{children(period)}</>
}
