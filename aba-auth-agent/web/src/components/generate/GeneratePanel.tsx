import { Check, Loader2, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { GenerationStatus, PeriodDetail, Validation } from '@/lib/types'

const STEPS = [
  { stage: 'drafting', label: 'Writing the narrative' },
  { stage: 'checking', label: 'Cross-checking the numbers against your data' },
] as const

function CrossCheck({ status }: { status: GenerationStatus }) {
  if (status.discrepancies && status.discrepancies.length > 0) {
    return (
      <Alert className="border-warning/50 bg-warning/10">
        <AlertTitle>
          {status.discrepancies.length} potential {status.discrepancies.length === 1 ? 'discrepancy' : 'discrepancies'} found
        </AlertTitle>
        <AlertDescription>
          <ul className="list-disc pl-5">
            {status.discrepancies.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </AlertDescription>
      </Alert>
    )
  }
  if (status.discrepancies) {
    return (
      <Alert className="border-success/40 bg-success/10">
        <AlertDescription>No discrepancies detected in the cross-check.</AlertDescription>
      </Alert>
    )
  }
  return (
    <Alert>
      <AlertTitle>The automatic number check couldn't run</AlertTitle>
      <AlertDescription>{status.check_error ?? 'Check the figures yourself before exporting.'}</AlertDescription>
    </Alert>
  )
}

/** The Generate button, its progress while the server works, and what the cross-check found. */
export function GeneratePanel({
  period,
  validation,
  status,
  error,
  working,
  onGenerate,
}: {
  period: PeriodDetail
  validation: Validation | null
  status: GenerationStatus
  error: string | null
  working: boolean
  onGenerate: () => void
}) {
  const [confirming, setConfirming] = useState(false)
  const hasDraft = period.narrative !== null
  const payor = period.client.payor_name
  const stageIndex = STEPS.findIndex((step) => step.stage === status.stage)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Write the narrative</CardTitle>
        <CardDescription>
          {period.template ? (
            <>
              Layout: your template “{period.template.name}” ({period.template.section_count} sections).
            </>
          ) : (
            <>
              Layout: built-in default. Add your own on the <Link className="underline" to="/templates">Templates</Link> page.
            </>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {validation && !validation.is_complete && (
          <Alert className="border-warning/50 bg-warning/10">
            <AlertTitle>Extracted data is incomplete ({Math.round(validation.score * 100)}%)</AlertTitle>
            <AlertDescription>
              The narrative will contain placeholders for the missing data.{' '}
              <Link className="underline" to={`/periods/${period.id}/review`}>
                Fill it in on Review
              </Link>
              .
            </AlertDescription>
          </Alert>
        )}

        <div>
          <Button onClick={() => (hasDraft ? setConfirming(true) : onGenerate())} disabled={working}>
            {working ? <Loader2 className="animate-spin" /> : <Sparkles />}
            {hasDraft ? `Regenerate ${payor} narrative` : `Generate ${payor} narrative`}
          </Button>
        </div>

        {working && (
          <ol className="grid gap-2 text-sm" aria-label="Progress">
            {STEPS.map((step, index) => (
              <li key={step.stage} className={index > stageIndex ? 'text-muted-foreground' : undefined}>
                <span className="inline-flex items-center gap-2">
                  {index < stageIndex ? <Check className="size-4 text-success" /> : index === stageIndex ? <Loader2 className="size-4 animate-spin" /> : <span className="size-4" />}
                  {step.label}
                </span>
              </li>
            ))}
            <li className="text-muted-foreground">This takes a minute or so. You can leave this page; the draft will be here when you return.</li>
          </ol>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {status.stage === 'error' && (
          <Alert variant="destructive">
            <AlertTitle>Generation failed</AlertTitle>
            <AlertDescription>
              {status.error}
              {hasDraft && ' Your previous draft is unchanged.'}
            </AlertDescription>
          </Alert>
        )}
        {status.stage === 'done' && (
          <div className="grid gap-3">
            <Alert className="border-success/40 bg-success/10">
              <AlertDescription>Narrative generated.</AlertDescription>
            </Alert>
            <CrossCheck status={status} />
          </div>
        )}
      </CardContent>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Replace the current draft?</DialogTitle>
            <DialogDescription>
              Regenerating writes a fresh draft from your latest data. Any edits you've made to the narrative text will be lost.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirming(false)}>
              Keep my draft
            </Button>
            <Button
              onClick={() => {
                setConfirming(false)
                onGenerate()
              }}
            >
              Regenerate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
