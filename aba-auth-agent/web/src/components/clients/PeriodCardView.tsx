import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { DeadlineBadge } from '@/components/clients/DeadlineBadge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'
import { formatDate, STATUS_LABEL } from '@/lib/deadlines'
import type { PeriodCard } from '@/lib/types'

const day = (iso: string | null) => (iso ? formatDate(iso.slice(0, 10)) : '—')

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="truncate text-sm font-medium" title={value}>
        {value}
      </dd>
    </div>
  )
}

/** Everything about one authorization period, with the next steps for it. */
export function PeriodCardView({ period }: { period: PeriodCard }) {
  const [notes, setNotes] = useState(period.notes)
  const [savedNotes, setSavedNotes] = useState(period.notes)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [justSaved, setJustSaved] = useState(false)

  async function saveNotes() {
    setSaving(true)
    setError(null)
    try {
      await api.saveNotes(period.id, notes)
      setSavedNotes(notes)
      setJustSaved(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save the notes.')
    } finally {
      setSaving(false)
    }
  }

  const validation = period.validation
  const counts = period.counts

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{STATUS_LABEL[period.status]}</Badge>
        <DeadlineBadge period={period} />
      </div>

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Fact label="Source" value={period.uploaded_filename ?? 'Not imported'} />
        <Fact label="Extracted" value={day(period.extracted_at)} />
        <Fact label="Exported" value={day(period.exported_at)} />
      </dl>

      {validation && (
        <div className="grid gap-1.5">
          <p className="text-sm">
            <strong>Completeness:</strong> {Math.round(validation.score * 100)}% · <strong>Missing:</strong> {validation.missing} ·{' '}
            <strong>Warnings:</strong> {validation.warnings}
          </p>
          <Progress value={Math.round(validation.score * 100)} aria-label="Completeness" />
        </div>
      )}

      {counts && (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="What was extracted">
          <li>
            <strong>Assessments:</strong> {counts.assessments}
          </li>
          <li>
            <strong>Skill targets:</strong> {counts.skill_targets}
          </li>
          <li>
            <strong>Behaviors:</strong> {counts.behaviors}
          </li>
          <li>
            <strong>Goals:</strong> {counts.goals}
          </li>
          <li>
            <strong>Hours codes:</strong> {counts.hours_codes}
          </li>
        </ul>
      )}

      {period.narrative && (
        <p className="text-sm">
          <strong>Narrative confidence:</strong> {Math.round(period.narrative.confidence * 100)}% · <strong>BCBA flags:</strong>{' '}
          {period.narrative.flags}
        </p>
      )}

      <div className="grid gap-2">
        <label htmlFor={`notes-${period.id}`} className="text-sm font-medium">
          BCBA notes
        </label>
        <Textarea
          id={`notes-${period.id}`}
          rows={2}
          value={notes}
          onChange={(e) => {
            setNotes(e.target.value)
            setJustSaved(false)
          }}
        />
        <div className="flex items-center gap-3">
          {notes !== savedNotes && (
            <Button size="sm" variant="secondary" onClick={() => void saveNotes()} disabled={saving}>
              {saving && <Loader2 className="animate-spin" />} Save notes
            </Button>
          )}
          {justSaved && notes === savedNotes && (
            <span className="text-sm text-muted-foreground" role="status">
              Notes saved.
            </span>
          )}
        </div>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      <div className="flex flex-wrap gap-2 border-t pt-4">
        {!period.has_data && (
          <Button asChild size="sm">
            <Link to="/import">Import a report</Link>
          </Button>
        )}
        {period.has_data && (
          <>
            <Button asChild size="sm" variant="outline">
              <Link to={`/periods/${period.id}/review`}>Review data</Link>
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link to={`/periods/${period.id}/generate`}>Generate</Link>
            </Button>
          </>
        )}
        {period.has_narrative && (
          <Button asChild size="sm" variant="outline">
            <Link to={`/periods/${period.id}/export`}>Export</Link>
          </Button>
        )}
      </div>
    </div>
  )
}
