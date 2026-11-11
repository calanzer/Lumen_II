import { useState } from 'react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import type { ClinicalData } from '@/lib/types'

/** Parses pasted JSON into the data shape, or says what's wrong with it. */
export function parseClinicalJson(text: string): { data: ClinicalData } | { error: string } {
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch (e) {
    return { error: `That isn't valid JSON: ${e instanceof Error ? e.message : 'could not read it'}` }
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return { error: 'Expected a JSON object.' }
  const record = parsed as Record<string, unknown>
  if (typeof record.client !== 'object' || record.client === null) return { error: 'The data needs a "client" section.' }
  return { data: parsed as ClinicalData }
}

/** For fixing something the form can't express. The server still checks everything on save. */
export function RawJsonDialog({ data, onApply }: { data: ClinicalData; onApply: (data: ClinicalData) => void }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (next) {
          setText(JSON.stringify(data, null, 2)) // start from what's on screen right now
          setError(null)
        }
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline">Raw JSON editor</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Raw JSON editor</DialogTitle>
          <DialogDescription>
            The full extracted data. Changes are checked before they're kept — a value the app can't accept is refused with a reason.
          </DialogDescription>
        </DialogHeader>
        <Textarea aria-label="Extracted data JSON" className="h-96 font-mono text-xs" value={text} onChange={(e) => setText(e.target.value)} />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              const result = parseClinicalJson(text)
              if ('error' in result) return setError(result.error)
              onApply(result.data)
              setOpen(false)
            }}
          >
            Apply JSON
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
