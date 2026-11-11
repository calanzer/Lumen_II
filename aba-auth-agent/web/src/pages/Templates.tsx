import { Loader2, Upload } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { PageHeader } from '@/components/PageHeader'
import { SectionRows } from '@/components/templates/SectionRows'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'
import { isAccepted } from '@/lib/files'
import { rowsFrom, templateProblem, toDraft, type Row } from '@/lib/templates'
import type { Payor, TemplateInfo } from '@/lib/types'

interface Draft {
  rows: Row[]
  styleNotes: string
  name: string
  sourceFilename: string
}

const message = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback)

export function Templates() {
  const [payors, setPayors] = useState<Payor[]>([])
  const [payor, setPayor] = useState<string | null>(null)
  const [info, setInfo] = useState<TemplateInfo | null>(null)
  const [drafts, setDrafts] = useState<Record<string, Draft>>({}) // one in-progress template per payor
  const [file, setFile] = useState<File | null>(null)
  const [fileKey, setFileKey] = useState(0)
  const [busy, setBusy] = useState<'analyzing' | 'saving' | 'resetting' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    api
      .payors()
      .then((loaded) => {
        setPayors(loaded)
        setPayor(loaded[0]?.key ?? null)
      })
      .catch((e) => setError(message(e, 'Could not load payors.')))
  }, [])

  useEffect(() => {
    if (!payor) return
    let cancelled = false
    setInfo(null)
    setFile(null)
    setFileKey((k) => k + 1)
    setError(null)
    setNotice(null)
    api
      .template(payor)
      .then((loaded) => !cancelled && setInfo(loaded))
      .catch((e) => !cancelled && setError(message(e, 'Could not load this template.')))
    return () => {
      cancelled = true
    }
  }, [payor])

  const draft = payor ? drafts[payor] : undefined
  const setDraft = useCallback((key: string, next: Draft | undefined) => {
    setDrafts((current) => {
      const copy = { ...current }
      if (next) copy[key] = next
      else delete copy[key]
      return copy
    })
  }, [])

  async function analyze() {
    if (!payor || !file) return
    setBusy('analyzing')
    setError(null)
    setNotice(null)
    try {
      const result = await api.analyzeTemplate(file)
      const payorName = payors.find((p) => p.key === payor)?.display_name ?? payor
      setDraft(payor, {
        rows: rowsFrom(result.sections),
        styleNotes: result.style_notes,
        name: `${payorName} — ${result.source_filename ?? file.name}`,
        sourceFilename: result.source_filename ?? file.name,
      })
    } catch (e) {
      setError(message(e, 'Could not analyze that report.'))
    } finally {
      setBusy(null)
    }
  }

  async function save() {
    if (!payor || !draft) return
    const problem = templateProblem(draft.name, draft.rows)
    if (problem) return setError(problem)
    setBusy('saving')
    setError(null)
    try {
      const saved = await api.saveTemplate(payor, draft.name.trim(), toDraft(draft.rows, draft.styleNotes, draft.sourceFilename))
      setInfo(saved)
      setDraft(payor, undefined)
      setFile(null)
      setFileKey((k) => k + 1)
      setNotice(`Template saved for ${saved.payor_name}.`)
    } catch (e) {
      setError(message(e, 'Could not save the template.'))
    } finally {
      setBusy(null)
    }
  }

  async function useDefault() {
    if (!payor) return
    setBusy('resetting')
    setError(null)
    try {
      setInfo(await api.useDefaultTemplate(payor))
      setNotice('Now using the built-in layout.')
    } catch (e) {
      setError(message(e, 'Could not switch to the default.'))
    } finally {
      setBusy(null)
    }
  }

  return (
    <>
      <PageHeader title="Templates" description="Teach the app how each payor's reauthorization report should be laid out." />

      <div className="grid gap-6">
        <div className="grid max-w-sm gap-2">
          <Label htmlFor="payor">Payor</Label>
          <Select value={payor ?? undefined} onValueChange={setPayor}>
            <SelectTrigger id="payor" className="w-full">
              <SelectValue placeholder="Choose a payor" />
            </SelectTrigger>
            <SelectContent>
              {payors.map((p) => (
                <SelectItem key={p.key} value={p.key}>
                  {p.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {notice && (
          <Alert className="border-success/40 bg-success/10" role="status">
            <AlertDescription>{notice}</AlertDescription>
          </Alert>
        )}

        <Card aria-label="Current template">
          {!info ? (
            <CardContent className="pt-6">
              <Skeleton className="h-24 w-full" aria-label="Loading template" />
            </CardContent>
          ) : info.active ? (
            <>
              <CardHeader>
                <CardTitle>Using your template: {info.active.name}</CardTitle>
                <CardDescription>
                  {info.active.sections.length} sections. New narratives for {info.payor_name} clients follow this layout.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4">
                <ol className="grid gap-1 pl-5 text-sm [list-style:decimal]">
                  {info.active.sections.map((section) => (
                    <li key={section.title}>
                      <strong>{section.title}</strong>
                      {section.guidance && <span className="text-muted-foreground"> — {section.guidance}</span>}
                    </li>
                  ))}
                </ol>
                {info.active.style_notes && <p className="text-sm text-muted-foreground">Style: {info.active.style_notes}</p>}
                <div>
                  <Button variant="outline" onClick={() => void useDefault()} disabled={busy !== null}>
                    Use the built-in default instead
                  </Button>
                </div>
              </CardContent>
            </>
          ) : (
            <>
              <CardHeader>
                <CardTitle>Using the built-in default layout</CardTitle>
                <CardDescription>Nine standard sections: {info.default_sections.join(', ')}.</CardDescription>
              </CardHeader>
            </>
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Create a template from a past report</CardTitle>
            <CardDescription>
              Upload a reauthorization report your practice has written for this payor. Only its section structure and writing style are
              kept. Client details are not copied, and the uploaded file is not stored.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Label htmlFor="past-report">Past report</Label>
            <Input
              key={fileKey}
              id="past-report"
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => {
                const chosen = e.target.files?.[0] ?? null
                if (chosen && !isAccepted(chosen.name)) {
                  setFile(null)
                  setError('Upload a PDF or Word (.docx) report.')
                  return
                }
                setError(null)
                setFile(chosen)
              }}
            />
            <div>
              <Button onClick={() => void analyze()} disabled={!file || busy !== null}>
                {busy === 'analyzing' ? <Loader2 className="animate-spin" /> : <Upload />}
                {busy === 'analyzing' ? 'Reading the report…' : 'Analyze report'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {draft && payor && (
          <Card aria-label="Review the detected sections">
            <CardHeader>
              <CardTitle>Review the detected sections</CardTitle>
              <CardDescription>
                Fix titles, edit what each section covers, reorder, add or delete sections. Nothing is saved until you click Save template.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5">
              <SectionRows rows={draft.rows} onChange={(rows) => setDraft(payor, { ...draft, rows })} />
              <div className="grid gap-2">
                <Label htmlFor="style">Writing style</Label>
                <Textarea id="style" rows={4} value={draft.styleNotes} onChange={(e) => setDraft(payor, { ...draft, styleNotes: e.target.value })} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="template-name">Template name</Label>
                <Input id="template-name" value={draft.name} onChange={(e) => setDraft(payor, { ...draft, name: e.target.value })} />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => void save()} disabled={busy !== null}>
                  {busy === 'saving' && <Loader2 className="animate-spin" />} Save template
                </Button>
                <Button variant="outline" onClick={() => setDraft(payor, undefined)} disabled={busy !== null}>
                  Discard
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  )
}
