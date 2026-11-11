import { Link, Navigate } from 'react-router'

import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { lastPeriod } from '@/hooks/usePeriod'

const TITLES = { review: 'Review data', generate: 'Generate', export: 'Export' }

/** The sidebar's Review / Generate / Export links: open that step for the period worked on last. */
export function PeriodRedirect({ step }: { step: keyof typeof TITLES }) {
  const id = lastPeriod.get()
  if (id) return <Navigate to={`/periods/${id}/${step}`} replace />
  return (
    <>
      <PageHeader title={TITLES[step]} />
      <Card>
        <CardHeader>
          <CardTitle>Choose a client first</CardTitle>
          <CardDescription>
            Open a client and pick an authorization period, or import a report — it will take you straight here.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to="/clients">Go to Clients</Link>
          </Button>
        </CardContent>
      </Card>
    </>
  )
}
