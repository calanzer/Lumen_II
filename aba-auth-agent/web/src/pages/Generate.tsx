import { ArrowRight } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'
import { Link, useParams } from 'react-router'

import { GeneratePanel } from '@/components/generate/GeneratePanel'
import { NarrativeEditor, type SectionText } from '@/components/generate/NarrativeEditor'
import { ProgressSince } from '@/components/generate/ProgressSince'
import { PeriodGate } from '@/components/period/PeriodGate'
import { PeriodHeader } from '@/components/period/PeriodHeader'
import { SaveStatus } from '@/components/period/SaveStatus'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useAutosave } from '@/hooks/useAutosave'
import { useGeneration } from '@/hooks/useGeneration'
import { usePeriod } from '@/hooks/usePeriod'
import { api } from '@/lib/api'
import type { Narrative, PeriodDetail } from '@/lib/types'

const textsOf = (narrative: Narrative): SectionText[] => narrative.sections.map((s) => ({ key: s.key, content: s.content }))

/** The draft and its editor. Remounted (via `key`) whenever a new draft arrives. */
function Draft({
  periodId,
  narrative,
  stale,
  discardRef,
}: {
  periodId: string
  narrative: Narrative
  stale: boolean
  /** Filled with a function that drops unsaved edits, for when the draft is about to be replaced */
  discardRef: RefObject<(() => void) | null>
}) {
  const { value, update, discard, state, error, saveNow } = useAutosave(textsOf(narrative), (texts) => api.saveNarrative(periodId, texts))
  useEffect(() => {
    discardRef.current = discard
  }, [discard, discardRef])

  return (
    <div className="grid gap-6">
      <div className="sticky top-0 z-10 -mx-1 flex flex-wrap items-center justify-between gap-3 border-b bg-background/95 px-1 py-3 backdrop-blur">
        <SaveStatus state={state} error={error} onRetry={() => void saveNow()} />
        <Button variant="outline" size="sm" onClick={() => void saveNow()} disabled={state === 'saved' || state === 'saving'}>
          Save all edits
        </Button>
      </div>

      {stale && (
        <Alert className="border-warning/50 bg-warning/10">
          <AlertDescription>
            <strong>This draft was written before your latest edits to the extracted data.</strong> Regenerate to include them.
            Regenerating replaces any edits you've made to the narrative text.
          </AlertDescription>
        </Alert>
      )}

      <div>
        <h2 className="text-lg font-semibold">BCBA review — edit narrative sections</h2>
        <p className="text-sm text-muted-foreground">
          <strong className="text-foreground">Left:</strong> source data for checking. <strong className="text-foreground">Right:</strong> the
          AI draft — edit it directly. Your clinical judgment takes precedence over the AI's text.
        </p>
      </div>

      <NarrativeEditor
        sections={narrative.sections}
        texts={value}
        onEdit={(key, content) =>
          update((draft) => {
            const entry = draft.find((t) => t.key === key)
            if (entry) entry.content = content
          })
        }
      />

      {narrative.flags.length > 0 && (
        <section aria-label="Items requiring BCBA attention" className="grid gap-2">
          <h2 className="text-lg font-semibold">
            Items requiring BCBA attention <span className="text-sm font-normal text-muted-foreground">({narrative.flags.length})</span>
          </h2>
          <ul className="grid gap-2">
            {narrative.flags.map((flag) => (
              <li key={flag} className="rounded-r-md border-l-4 border-warning bg-warning/10 px-3 py-2 text-sm">
                {flag}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex justify-end border-t pt-4">
        <Button asChild>
          <Link to={`/periods/${periodId}/export`}>
            Continue to Export <ArrowRight />
          </Link>
        </Button>
      </div>
    </div>
  )
}

function GenerateBody({ period, reload }: { period: PeriodDetail; reload: () => Promise<void> }) {
  const [version, setVersion] = useState(0)
  const discardRef = useRef<(() => void) | null>(null)

  const finished = useCallback(() => {
    void reload().then(() => setVersion((v) => v + 1)) // new draft: fresh editor
  }, [reload])
  const generation = useGeneration(period.id, finished)

  return (
    <div className="grid gap-6">
      {period.comparison && <ProgressSince comparison={period.comparison} />}
      <GeneratePanel
        period={period}
        validation={period.validation}
        status={generation.status}
        error={generation.error}
        working={generation.working}
        onGenerate={() => {
          discardRef.current?.() // the confirmed replacement must not be overwritten by a late autosave
          void generation.start()
        }}
      />
      {period.narrative && (
        <Draft
          key={`${period.id}:${version}`}
          periodId={period.id}
          narrative={period.narrative}
          stale={period.narrative.stale}
          discardRef={discardRef}
        />
      )}
    </div>
  )
}

export function Generate() {
  const { periodId } = useParams()
  const { period, error, reload } = usePeriod(periodId)
  return (
    <>
      {period && <PeriodHeader period={period} current="generate" />}
      <PeriodGate period={period} error={error} retry={() => void reload()} needs="data">
        {(loaded) => <GenerateBody period={loaded} reload={reload} />}
      </PeriodGate>
    </>
  )
}
