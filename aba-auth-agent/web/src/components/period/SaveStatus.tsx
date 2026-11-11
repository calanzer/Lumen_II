import { AlertCircle, Check, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { SaveState } from '@/hooks/useAutosave'

/** "All changes saved" / "Saving…" / why a save was refused. */
export function SaveStatus({ state, error, onRetry }: { state: SaveState; error: string | null; onRetry: () => void }) {
  if (state === 'error') {
    return (
      <p className="flex flex-wrap items-center gap-2 text-sm text-destructive" role="alert">
        <AlertCircle className="size-4" />
        <span>Not saved: {error}</span>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </p>
    )
  }
  return (
    <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
      {state === 'saved' ? <Check className="size-4 text-success" /> : <Loader2 className="size-4 animate-spin" />}
      {state === 'saved' ? 'All changes saved' : state === 'saving' ? 'Saving…' : 'Unsaved changes…'}
    </p>
  )
}
