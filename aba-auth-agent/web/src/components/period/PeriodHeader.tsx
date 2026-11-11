import { ArrowLeft, Check } from 'lucide-react'
import { Link } from 'react-router'

import { Badge } from '@/components/ui/badge'
import { formatDate, STATUS_LABEL } from '@/lib/deadlines'
import type { PeriodDetail } from '@/lib/types'
import { cn } from '@/lib/utils'

export type Step = 'review' | 'generate' | 'export'

const STEPS: { step: Step; label: string }[] = [
  { step: 'review', label: 'Review data' },
  { step: 'generate', label: 'Generate' },
  { step: 'export', label: 'Export' },
]

/** Who and which authorization period this is, and the three steps to get it submitted. */
export function PeriodHeader({ period, current }: { period: PeriodDetail; current: Step }) {
  const available: Record<Step, boolean> = {
    review: period.data !== null,
    generate: period.data !== null,
    export: period.narrative !== null,
  }
  return (
    <header className="mb-6 grid gap-4 border-b pb-4">
      <div>
        <Link to="/clients" className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-3.5" /> Clients
        </Link>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <h1 className="text-3xl font-bold tracking-tight">{period.client.display_name}</h1>
          <Badge variant="secondary">{STATUS_LABEL[period.status]}</Badge>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {period.client.client_identifier ?? 'No client ID'} · {period.client.payor_name} · {formatDate(period.period_start)} to{' '}
          {formatDate(period.period_end)}
        </p>
      </div>
      <nav aria-label="Reauthorization steps">
        <ol className="flex flex-wrap gap-2">
          {STEPS.map(({ step, label }, index) => {
            const isCurrent = step === current
            const classes = cn(
              'inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm',
              isCurrent && 'border-primary bg-accent font-medium text-accent-foreground',
              !isCurrent && available[step] && 'hover:bg-muted',
              !available[step] && 'text-muted-foreground opacity-60',
            )
            const content = (
              <>
                <span className="flex size-5 items-center justify-center rounded-full bg-muted text-xs">
                  {index < STEPS.findIndex((s) => s.step === current) ? <Check className="size-3" /> : index + 1}
                </span>
                {label}
              </>
            )
            return (
              <li key={step}>
                {available[step] ? (
                  <Link to={`/periods/${period.id}/${step}`} className={classes} aria-current={isCurrent ? 'step' : undefined}>
                    {content}
                  </Link>
                ) : (
                  <span className={classes} aria-disabled="true">
                    {content}
                  </span>
                )}
              </li>
            )
          })}
        </ol>
      </nav>
    </header>
  )
}
