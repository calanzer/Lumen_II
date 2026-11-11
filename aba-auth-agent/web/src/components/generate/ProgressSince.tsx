import { ArrowDown, ArrowUp } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate } from '@/lib/deadlines'
import type { Comparison } from '@/lib/types'

/** How this period compares with the one before it: skills mastered, targets, behavior trends. */
export function ProgressSince({ comparison }: { comparison: Comparison }) {
  const gained = comparison.skills_mastered - comparison.skills_mastered_prior
  return (
    <Card>
      <CardHeader>
        <CardTitle>Progress since prior authorization</CardTitle>
        <CardDescription>
          Compared with {formatDate(comparison.prior_start)} to {formatDate(comparison.prior_end)}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <dl className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-sm text-muted-foreground">Skills mastered</dt>
            <dd className="text-2xl font-semibold">
              {comparison.skills_mastered}{' '}
              <span className={gained > 0 ? 'text-base text-success' : 'text-base text-muted-foreground'}>
                {gained > 0 ? `+${gained}` : gained}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Current skill targets</dt>
            <dd className="text-2xl font-semibold">{comparison.skill_targets}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Current behavior targets</dt>
            <dd className="text-2xl font-semibold">{comparison.behavior_targets}</dd>
          </div>
        </dl>
        {comparison.behavior_changes.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-medium">Behavior trends</h3>
            <ul className="grid gap-1 text-sm">
              {comparison.behavior_changes.map((change) => {
                const down = change.percent_change < 0
                return (
                  <li key={change.name} className="flex flex-wrap items-center gap-x-2">
                    <strong>{change.name}</strong>
                    <span>
                      {change.prior} → {change.current} {change.unit}
                    </span>
                    <span className={down ? 'inline-flex items-center text-success' : 'inline-flex items-center text-destructive'}>
                      {down ? <ArrowDown className="size-3.5" /> : <ArrowUp className="size-3.5" />}
                      {Math.abs(change.percent_change).toFixed(0)}% {down ? 'decrease' : 'increase'}
                    </span>
                  </li>
                )
              })}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
