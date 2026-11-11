import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { attentionLists } from '@/lib/attention'
import { formatDate } from '@/lib/deadlines'
import type { ImportResult } from '@/lib/types'

function Metric({ label, value, tone }: { label: string; value: ReactNode; tone?: 'ok' | 'warn' }) {
  return (
    <Card className="gap-1 py-4" role="group" aria-label={label}>
      <CardContent className="px-4">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className={`mt-1 text-2xl font-semibold ${tone === 'warn' ? 'text-warning' : tone === 'ok' ? 'text-success' : ''}`}>{value}</p>
      </CardContent>
    </Card>
  )
}

export function ImportResultView({ result, filename, onAnother }: { result: ImportResult; filename: string; onAnother: () => void }) {
  const lists = attentionLists(result)
  const firstWithItems = lists.find((list) => list.items.length > 0)
  const draft = result.draft

  return (
    <div className="grid gap-5">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Imported {filename}</CardTitle>
          <CardDescription>
            {result.client.display_name} · {result.payor.name} · {formatDate(result.period.start)} to {formatDate(result.period.end)}
          </CardDescription>
        </CardHeader>
        {result.notes.length > 0 && (
          <CardContent className="grid gap-1 text-sm text-muted-foreground">
            {result.notes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </CardContent>
        )}
      </Card>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="Data completeness" value={`${Math.round(result.completeness * 100)}%`} tone={result.completeness >= 0.8 ? 'ok' : 'warn'} />
        <Metric label="Missing required" value={result.missing.length} tone={result.missing.length ? 'warn' : 'ok'} />
        <Metric label="Draft flags" value={draft ? draft.flags.length : 'n/a'} />
        <Metric label="Numbers to verify" value={result.discrepancies ? result.discrepancies.length : 'n/a'} />
      </div>

      {result.draft_error && (
        <Alert variant="destructive">
          <AlertTitle>The narrative couldn't be drafted</AlertTitle>
          <AlertDescription>
            The report's data was saved. {result.draft_error} You can generate the narrative from the Generate screen.
          </AlertDescription>
        </Alert>
      )}
      {draft && (
        <Alert className="border-success/40 bg-success/10">
          <AlertTitle>
            Draft written: {draft.section_count} sections, {draft.sections_needing_review} need your review
          </AlertTitle>
          {!draft.used_custom_template && (
            <AlertDescription>
              Drafted in the built-in layout. Add this payor's own layout on the Templates screen and future drafts will follow it.
            </AlertDescription>
          )}
        </Alert>
      )}
      {draft && result.discrepancies === null && (
        <Alert className="border-warning/40 bg-warning/10">
          <AlertTitle>The automatic number check couldn't run</AlertTitle>
          <AlertDescription>
            {result.check_error ? `${result.check_error} ` : ''}Check the draft's numbers against the data yourself.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">What needs your eyes</CardTitle>
        </CardHeader>
        <CardContent>
          {firstWithItems ? (
            <Tabs defaultValue={firstWithItems.key}>
              <TabsList className="h-auto flex-wrap">
                {lists.map((list) => (
                  <TabsTrigger key={list.key} value={list.key}>
                    {list.label}
                    <Badge variant="secondary" className="ml-1">
                      {list.items.length}
                    </Badge>
                  </TabsTrigger>
                ))}
              </TabsList>
              {lists.map((list) => (
                <TabsContent key={list.key} value={list.key}>
                  {list.items.length ? (
                    <ul className="mt-2 grid list-disc gap-2 pl-5 text-sm">
                      {list.items.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-muted-foreground">Nothing here.</p>
                  )}
                </TabsContent>
              ))}
            </Tabs>
          ) : (
            <p className="text-sm text-muted-foreground">Nothing was flagged.</p>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link to={`/periods/${result.period_id}/review`}>Review the data</Link>
        </Button>
        {draft && (
          <Button asChild variant="outline">
            <Link to={`/periods/${result.period_id}/generate`}>Open the draft</Link>
          </Button>
        )}
        <Button variant="outline" onClick={onAnother}>
          Import another report
        </Button>
      </div>
    </div>
  )
}
