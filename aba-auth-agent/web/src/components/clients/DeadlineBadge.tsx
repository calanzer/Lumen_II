import { Badge } from '@/components/ui/badge'
import { deadlineTone, describeDays, STATUS_LABEL } from '@/lib/deadlines'
import type { PeriodSummary } from '@/lib/types'
import { cn } from '@/lib/utils'

/** How close an authorization is to ending, or its status once the work is done. */
export function DeadlineBadge({ period }: { period: PeriodSummary }) {
  const tone = deadlineTone(period)
  if (tone === 'done') {
    return (
      <Badge variant="secondary" data-tone={tone}>
        {STATUS_LABEL[period.status]}
      </Badge>
    )
  }
  return (
    <Badge
      data-tone={tone}
      variant={tone === 'expired' ? 'destructive' : tone === 'ok' ? 'outline' : 'default'}
      className={cn(tone === 'urgent' && 'bg-warning text-warning-foreground', tone === 'soon' && 'bg-warning/15 text-foreground')}
    >
      {describeDays(period.days_until_end)}
    </Badge>
  )
}
