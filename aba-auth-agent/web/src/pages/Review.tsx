import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'


import { PeriodGate } from '@/components/period/PeriodGate'
import { PeriodHeader } from '@/components/period/PeriodHeader'
import { SaveStatus } from '@/components/period/SaveStatus'
import { RawJsonDialog } from '@/components/review/RawJsonDialog'
import {
  Assessments,
  Behaviors,
  Caregiver,
  Demographics,
  Discharge,
  Goals,
  Hours,
  RequestedHours,
  Skills,
} from '@/components/review/sections'
import { ValidationBanner } from '@/components/review/ValidationBanner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAutosave } from '@/hooks/useAutosave'
import { usePeriod } from '@/hooks/usePeriod'
import { api } from '@/lib/api'
import type { PeriodDetail } from '@/lib/types'

function ReviewForm({ period }: { period: PeriodDetail }) {
  const [validation, setValidation] = useState(period.validation)
  const [stale, setStale] = useState(period.narrative?.stale ?? false)
  const {
    value: data,
    update,
    replace,
    state,
    error,
    saveNow,
  } = useAutosave(
    period.data!,
    (edited) => api.saveData(period.id, edited),
    (saved) => {
      setValidation(saved.validation)
      setStale(saved.narrative_stale)
    },
  )

  return (
    <div className="grid gap-6">
      <div className="sticky top-0 z-10 -mx-1 flex flex-wrap items-center justify-between gap-3 border-b bg-background/95 px-1 py-3 backdrop-blur">
        <SaveStatus state={state} error={error} onRetry={() => void saveNow()} />
        <Button variant="outline" size="sm" onClick={() => void saveNow()} disabled={state === 'saved' || state === 'saving'}>
          Save now
        </Button>
      </div>

      {stale && (
        <Alert className="border-warning/50 bg-warning/10">
          <AlertDescription>
            You've changed the data since the narrative was written.{' '}
            <Link className="font-medium underline" to={`/periods/${period.id}/generate`}>
              Regenerate it
            </Link>{' '}
            so the document matches.
          </AlertDescription>
        </Alert>
      )}

      {validation && <ValidationBanner validation={validation} />}

      <Demographics data={data} update={update} />
      <Assessments data={data} update={update} />
      <Skills data={data} update={update} />
      <Behaviors data={data} update={update} />
      <Hours data={data} update={update} />
      <Goals data={data} update={update} />
      <Caregiver data={data} update={update} />
      <Discharge data={data} update={update} />
      <RequestedHours data={data} update={update} />

      {data.confidence_notes.length > 0 && (
        <details className="rounded-md border px-4 py-3 text-sm">
          <summary className="cursor-pointer font-medium">Extraction confidence notes ({data.confidence_notes.length})</summary>
          <ul className="mt-2 list-disc pl-6">
            {data.confidence_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </details>
      )}
      {data.missing_fields.length > 0 && (
        <details open className="rounded-md border px-4 py-3 text-sm">
          <summary className="cursor-pointer font-medium">Missing fields ({data.missing_fields.length})</summary>
          <ul className="mt-2 list-disc pl-6">
            {data.missing_fields.map((field) => (
              <li key={field}>{field}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
        <RawJsonDialog data={data} onApply={replace} />
        <Button asChild>
          <Link to={`/periods/${period.id}/generate`}>
            Continue to Generate <ArrowRight />
          </Link>
        </Button>
      </div>
    </div>
  )
}

export function Review() {
  const { periodId } = useParams()
  const { period, error, reload } = usePeriod(periodId)
  return (
    <>
      {period && <PeriodHeader period={period} current="review" />}
      <PeriodGate period={period} error={error} retry={() => void reload()} needs="data">
        {(loaded) => <ReviewForm key={loaded.id} period={loaded} />}
      </PeriodGate>
    </>
  )
}
