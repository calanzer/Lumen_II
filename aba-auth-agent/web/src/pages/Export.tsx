import { CheckCircle2, Download, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import { PeriodGate } from '@/components/period/PeriodGate'
import { PeriodHeader } from '@/components/period/PeriodHeader'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { usePeriod } from '@/hooks/usePeriod'
import { api, type Download as DownloadedFile } from '@/lib/api'
import { formatDate } from '@/lib/deadlines'
import { saveBlob } from '@/lib/files'
import type { Payor, PeriodDetail } from '@/lib/types'

function Metric({ label, value, tone }: { label: string; value: string; tone: 'good' | 'warn' }) {
  return (
    <Card className={tone === 'good' ? 'border-l-4 border-l-success' : 'border-l-4 border-l-warning'}>
      <CardContent className="pt-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="text-3xl font-bold">{value}</p>
      </CardContent>
    </Card>
  )
}

function ExportBody({ period, reload }: { period: PeriodDetail; reload: () => Promise<void> }) {
  const narrative = period.narrative!
  const custom = narrative.kind === 'custom'
  const [payors, setPayors] = useState<Payor[]>([])
  const [payorKey, setPayorKey] = useState(narrative.payor_key ?? period.client.payor)
  const [confirmed, setConfirmed] = useState(false)
  const [building, setBuilding] = useState(false)
  const [file, setFile] = useState<DownloadedFile | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    api.payors().then(setPayors).catch(() => {}) // the picker just stays empty; the client's payor is still used
  }, [])

  const needReview = narrative.sections.filter((s) => s.requires_review).length
  const confidence = Math.round(narrative.overall_confidence * 100)
  const payorName = payors.find((p) => p.key === (narrative.payor_key ?? period.client.payor))?.display_name ?? period.client.payor_name

  async function build() {
    setBuilding(true)
    setError(null)
    try {
      const built = await api.exportPeriod(period.id, custom ? undefined : payorKey)
      setFile(built)
      saveBlob(built.blob, built.filename)
      await reload() // now marked exported
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The Word document could not be built.')
    } finally {
      setBuilding(false)
    }
  }

  async function markSubmitted() {
    setSubmitting(true)
    setError(null)
    try {
      await api.markSubmitted(period.id)
      await reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not update the status.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="grid gap-6">
      {narrative.stale && (
        <Alert className="border-warning/50 bg-warning/10">
          <AlertDescription>
            <strong>The narrative was written before your latest edits to the extracted data.</strong> Go to{' '}
            <Link className="underline" to={`/periods/${period.id}/generate`}>
              Generate
            </Link>{' '}
            and regenerate it so the document matches your reviewed data.
          </AlertDescription>
        </Alert>
      )}

      <section aria-label="Export summary" className="grid gap-4">
        <h2 className="text-lg font-semibold">Export summary</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <Card className={`border-l-4 ${confidence >= 80 ? 'border-l-success' : 'border-l-warning'}`}>
            <CardContent className="grid gap-2 pt-6">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Confidence</p>
              <p className="text-3xl font-bold">{confidence}%</p>
              <Progress value={confidence} aria-label="Confidence" />
            </CardContent>
          </Card>
          <Metric label="BCBA flags" value={String(narrative.flags.length)} tone={narrative.flags.length === 0 ? 'good' : 'warn'} />
          <Metric label="Sections needing review" value={String(needReview)} tone={needReview === 0 ? 'good' : 'warn'} />
        </div>
        {needReview > 0 && (
          <Alert className="border-warning/50 bg-warning/10">
            <AlertTitle>{needReview} {needReview === 1 ? 'section still needs' : 'sections still need'} review.</AlertTitle>
            <AlertDescription>Make sure these are resolved before submitting to the payor.</AlertDescription>
          </Alert>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Payor template</CardTitle>
          {custom && (
            <CardDescription>
              This narrative follows your template “{narrative.template_name}” for {payorName}.
            </CardDescription>
          )}
        </CardHeader>
        {!custom && (
          <CardContent className="grid gap-2">
            <Label htmlFor="payor">Choose the payor template for your Word document</Label>
            <Select value={payorKey} onValueChange={setPayorKey}>
              <SelectTrigger id="payor" className="w-full sm:max-w-md">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(payors.length > 0 ? payors : [{ key: payorKey, display_name: period.client.payor_name, subtitle: '', has_custom_template: false }]).map((p) => (
                  <SelectItem key={p.key} value={p.key}>
                    {p.display_name}
                    {p.subtitle && ` — ${p.subtitle}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        )}
      </Card>

      <Card>
        <CardContent className="grid gap-4 pt-6">
          <div className="flex items-start gap-3 rounded-md bg-accent p-4">
            <Checkbox id="confirm" checked={confirmed} onCheckedChange={(state) => setConfirmed(state === true)} className="mt-0.5" />
            <Label htmlFor="confirm" className="leading-snug">
              I have reviewed all sections and confirm this document is clinically accurate.
            </Label>
          </div>
          <div>
            <Button onClick={() => void build()} disabled={!confirmed || building}>
              {building ? <Loader2 className="animate-spin" /> : <Download />}
              Generate Word document
            </Button>
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {file && (
            <Alert className="border-success/40 bg-success/10">
              <CheckCircle2 />
              <AlertTitle>Document ready: {file.filename}</AlertTitle>
              <AlertDescription className="grid gap-2">
                <span>It should have started downloading. If not:</span>
                <Button variant="outline" size="sm" className="w-fit" onClick={() => saveBlob(file.blob, file.filename)}>
                  <Download /> Download again
                </Button>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {period.status === 'exported' && (
        <Card>
          <CardHeader>
            <CardTitle>After submitting to the payor</CardTitle>
            <CardDescription>
              Once you've submitted this document to the payor, mark it here so your client list shows it's done.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => void markSubmitted()} disabled={submitting}>
              {submitting && <Loader2 className="animate-spin" />} Mark as submitted to payor
            </Button>
          </CardContent>
        </Card>
      )}
      {period.status === 'submitted' && (
        <Alert className="border-success/40 bg-success/10">
          <CheckCircle2 />
          <AlertTitle>Submitted to the payor</AlertTitle>
          <AlertDescription>
            {period.exported_at ? `Exported ${formatDate(period.exported_at.slice(0, 10))}. ` : ''}Nothing more to do for this authorization.
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}

export function Export() {
  const { periodId } = useParams()
  const { period, error, reload } = usePeriod(periodId)
  return (
    <>
      {period && <PeriodHeader period={period} current="export" />}
      <PeriodGate period={period} error={error} retry={() => void reload()} needs="narrative">
        {(loaded) => <ExportBody key={loaded.id} period={loaded} reload={reload} />}
      </PeriodGate>
    </>
  )
}
