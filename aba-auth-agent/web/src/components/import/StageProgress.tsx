import { Check, Loader2 } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { currentStep, STEPS } from '@/hooks/useImportJob'
import type { Stage } from '@/lib/types'
import { cn } from '@/lib/utils'

export function StageProgress({ stage, filename }: { stage: Stage; filename: string }) {
  const step = currentStep(stage)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="truncate text-base">{filename}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-5">
        <Progress value={(step / STEPS.length) * 100} aria-label="Import progress" />
        <ol className="grid gap-3">
          {STEPS.map(({ label }, index) => {
            const done = index < step
            const active = index === step
            return (
              <li
                key={label}
                aria-current={active ? 'step' : undefined}
                className={cn('flex items-center gap-3 text-sm', !done && !active && 'text-muted-foreground')}
              >
                <span
                  className={cn(
                    'flex size-6 items-center justify-center rounded-full border',
                    done && 'border-success bg-success text-success-foreground',
                    active && 'border-primary text-primary',
                  )}
                >
                  {done ? <Check className="size-3.5" /> : active ? <Loader2 className="size-3.5 animate-spin" /> : index + 1}
                </span>
                {label}
              </li>
            )
          })}
        </ol>
        <p className="text-xs text-muted-foreground">This takes a minute or two. You can leave this page open while it works.</p>
      </CardContent>
    </Card>
  )
}
